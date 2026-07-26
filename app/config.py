from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Type


def _parse_origins(value: str | None) -> list[str]:
    raw = value or "http://127.0.0.1:5000,http://localhost:5000"
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///instance/chess.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    SOCKETIO_ALLOWED_ORIGINS = _parse_origins(
        os.getenv("SOCKETIO_ALLOWED_ORIGINS")
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-only-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


_CONFIGS: dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None) -> Type[BaseConfig]:
    normalized = (name or "development").strip().lower()
    try:
        return _CONFIGS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_CONFIGS))
        raise ValueError(
            f"Unsupported APP_ENV '{normalized}'. Expected one of: {supported}."
        ) from exc


def validate_runtime_config(app_env: str, config: dict) -> None:
    if app_env != "production":
        return

    secret_key = config.get("SECRET_KEY")
    if not secret_key or len(secret_key) < 32:
        raise RuntimeError(
            "Production requires SECRET_KEY with at least 32 characters."
        )

    database_url = str(config.get("SQLALCHEMY_DATABASE_URI") or "")
    if database_url.startswith("sqlite:"):
        raise RuntimeError(
            "Production requires DATABASE_URL for a non-SQLite database."
        )

    allowed_origins = config.get("SOCKETIO_ALLOWED_ORIGINS") or []
    if "*" in allowed_origins:
        raise RuntimeError(
            "Production does not allow wildcard Socket.IO origins."
        )
