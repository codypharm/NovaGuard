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
    
    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    
    # Nova API (OpenAI Compatible)
    nova_api_key: str | None = None

    # Valyu Bio Search
    valyu_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
