"""Configuration for MCP Calculator server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        case_sensitive=False,  # Accept HOST, PORT, API_KEY (uppercase)
        extra="ignore",
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8016

    # Authentication
    api_key: str = "dev-api-key"

    # Feature flags
    debug: bool = False


settings = Settings()
