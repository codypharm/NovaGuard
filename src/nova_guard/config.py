"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/nova_guard"

    # OpenFDA API
    openfda_api_key: str | None = None

    # Application
    log_level: str = "INFO"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
