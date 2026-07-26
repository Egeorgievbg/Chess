from __future__ import annotations

import importlib
import os
import secrets

from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from app.config import get_config, validate_runtime_config


db = SQLAlchemy()
login_manager = LoginManager()

try:
    import gevent  # noqa: F401

    _async_mode = "gevent"
except ImportError:
    _async_mode = "threading"

socketio = SocketIO(async_mode=_async_mode)


def create_app(config_name: str | None = None) -> Flask:
    app_env = (config_name or os.getenv("APP_ENV") or "development").lower()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config(app_env))

    if not app.config.get("SECRET_KEY"):
        if app_env == "production":
            raise RuntimeError("Production requires the SECRET_KEY environment variable.")
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    validate_runtime_config(app_env, app.config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Моля, влезте в профила си, за да продължите."

    socketio.init_app(
        app,
        cors_allowed_origins=app.config["SOCKETIO_ALLOWED_ORIGINS"],
    )

    from app.routes.auth import auth_bp
    from app.routes.game import game_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(game_bp, url_prefix="/game")

    with app.app_context():
        # Temporary compatibility path. A later migration PR will replace
        # create_all() with versioned Alembic migrations.
        db.create_all()
        importlib.import_module("app.socket_events")

    return app
