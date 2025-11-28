"""Configuration for MCP Scratchpad server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Server settings (standardized env vars)
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Authentication
    api_key: str = "dev-scratchpad-key"  # Fixed API key for authentication
    
    # Feature flags
    debug: bool = False


settings = Settings()
