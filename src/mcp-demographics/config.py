"""Configuration for MCP Demographics server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8014

    # Authentication
    api_key: str = "dev-demographics-key"

    # Feature flags
    debug: bool = False


settings = Settings()
