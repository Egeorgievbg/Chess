import pytest

from app import create_app


def test_testing_app_starts_and_serves_homepage():
    app = create_app("testing")

    assert app.testing is True
    assert app.config["SECRET_KEY"] == "test-only-secret-key"
    assert "*" not in app.config["SOCKETIO_ALLOWED_ORIGINS"]

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200


def test_unknown_environment_is_rejected():
    with pytest.raises(ValueError, match="Unsupported APP_ENV"):
        create_app("unknown-environment")
