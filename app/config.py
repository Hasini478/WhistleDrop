"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or .env file."""

    # Moderator credentials for HTTP Basic Authentication
    MODERATOR_USERNAME: str = "moderator"
    MODERATOR_PASSWORD: str = "change-this-password"

    # Secret key for HMAC-SHA256 case code hashing
    SECRET_KEY: str = "replace-with-a-long-random-secret"

    # Database connection URL
    DATABASE_URL: str = "sqlite:///./whistledrop.db"

    # API configuration
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "WhistleDrop API"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of Settings."""
    return Settings()
