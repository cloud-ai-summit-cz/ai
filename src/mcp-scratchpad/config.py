"""Configuration for MCP Scratchpad server."""

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
    port: int = 8080
    
    # Authentication
    api_key: str = "dev-scratchpad-key"
    
    # Feature flags
    debug: bool = False


settings = Settings()
