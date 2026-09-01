from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-change-me"  # noqa: S105  # placeholder, refused in production


class Settings(BaseSettings):
    """Application settings, read from the environment once per process."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://caiame:caiame@localhost:5433/caiame",
        alias="DATABASE_URL",
    )
    cors_origins: list[str] = Field(default=["http://localhost:5173"], alias="CORS_ORIGINS")
    # Адрес, по которому сайт открывают люди. Нужен там, где ссылку строит сервер:
    # карта сайта состоит из абсолютных адресов, и взять их из заголовка запроса нельзя —
    # заголовок пишет тот, кто запрашивает.
    site_url: str = Field(default="http://localhost:5173", alias="SITE_URL")
    environment: Literal["development", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    api_prefix: str = "/api/v1"
    echo_sql: bool = Field(default=False, alias="ECHO_SQL")

    # Development default. Production must override it: a shared secret in source is a
    # secret everyone with repository access can sign tokens with.
    jwt_secret: str = Field(default=DEV_JWT_SECRET, alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Off over plain http in development; the deployment sets it, and the cookie is
    # worthless to an attacker on the wire once it is on.
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")

    redis_url: str = Field(default="redis://localhost:6380/0", alias="REDIS_URL")

    # Object storage for lecture material. Defaults point at the MinIO in docker-compose, so
    # a fresh clone can upload a file without an account anywhere; production overrides all
    # five. Two buckets rather than two prefixes: the access policy is set on the bucket,
    # and one wrong line in a shared policy would open the paid material.
    media_endpoint: str = Field(default="http://localhost:9100", alias="MEDIA_S3_ENDPOINT")
    media_region: str = Field(default="us-east-1", alias="MEDIA_S3_REGION")
    media_access_key: str = Field(default="caiame", alias="MEDIA_S3_ACCESS_KEY")
    media_secret_key: str = Field(default="caiame-dev-secret", alias="MEDIA_S3_SECRET_KEY")
    media_bucket_private: str = Field(default="caiame-private", alias="MEDIA_BUCKET_PRIVATE")
    media_bucket_public: str = Field(default="caiame-public", alias="MEDIA_BUCKET_PUBLIC")

    # An upload link is used once, right away; a playback link has to outlive the lecture
    # itself, because the browser re-requests byte ranges of a video on the same URL.
    upload_link_ttl_seconds: int = 60 * 60
    playback_link_ttl_seconds: int = 12 * 60 * 60

    # Windows are generous enough that a person mistyping a password never notices them,
    # and tight enough that guessing is pointless.
    login_attempts_per_ip: int = 20
    login_attempts_per_account: int = 10
    login_window_seconds: int = 15 * 60
    register_attempts_per_ip: int = 5
    register_window_seconds: int = 60 * 60

    @model_validator(mode="after")
    def refuse_placeholder_secret_in_production(self) -> Self:
        """
        Fail to start rather than sign tokens with a secret that is public.

        A shared JWT secret is a token-forging key: anyone who can read the repository could
        mint an admin session. Better a crash on deploy than a silent hole.
        """
        if self.environment == "production" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set in production")
        return self

    @property
    def refresh_cookie_path(self) -> str:
        """Scope the refresh cookie to the auth routes, so it is not sent with every request."""
        return f"{self.api_prefix}/auth"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor, so the environment is parsed once and the object is shared."""
    return Settings()
