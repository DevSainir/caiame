"""Settings that must refuse to start rather than start insecure."""

import pytest

from core.config import DEV_JWT_SECRET, Settings


def test_production_refuses_the_placeholder_secret() -> None:
    """
    The placeholder is in the repository, so in production it is a token-forging key.

    Crashing on deploy is loud; signing sessions with a public secret is silent.
    """
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(ENVIRONMENT="production", JWT_SECRET=DEV_JWT_SECRET)


def test_production_starts_with_a_real_secret() -> None:
    """A configured deployment is not blocked by the guard."""
    settings = Settings(ENVIRONMENT="production", JWT_SECRET="a-real-deployment-secret")

    assert settings.environment == "production"


def test_development_keeps_the_placeholder() -> None:
    """Local work must not require ceremony."""
    assert Settings().jwt_secret == DEV_JWT_SECRET


def test_refresh_cookie_is_scoped_to_the_auth_routes() -> None:
    """The cookie should not ride along on every catalogue request."""
    assert Settings().refresh_cookie_path == "/api/v1/auth"
