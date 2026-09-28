"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "dev-secret-change-me"
DEFAULT_JWT_SECRET = "dev-jwt-secret-change-me"


class Settings(BaseSettings):
    """Centralised configuration. Loaded from .env file or process env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(default="sqlite:///./crm_splash.db")

    # Security
    secret_key: str = Field(default=DEFAULT_SECRET_KEY)
    jwt_secret: str = Field(default=DEFAULT_JWT_SECRET)
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=1440)

    # Storage
    storage_root: str = Field(default="./storage")
    storage_url_max_age_seconds: int = Field(default=3600)
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024)

    # CORS
    cors_origins: str = Field(default="http://localhost:3000")

    # Rate limiting
    rate_limit_per_minute: int = Field(default=120)

    # Logging
    log_level: str = Field(default="INFO")

    # Environment
    env: str = Field(default="development")

    @model_validator(mode="after")
    def _reject_default_secrets_outside_dev(self) -> "Settings":
        if self.env in ("development", "test"):
            return self
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET is set to the insecure development default. "
                "Generate a strong secret (e.g. "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\") "
                "and set it via environment or .env before running outside dev/test."
            )
        if self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY is set to the insecure development default. "
                "Generate a strong secret and set it via environment or .env "
                "before running outside dev/test."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_root).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
