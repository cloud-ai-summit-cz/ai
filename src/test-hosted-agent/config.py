"""Configuration for test hosted agent."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Agent identity
    agent_name: str = "test-hosted-agent"

    # Azure AI Foundry connection
    azure_ai_foundry_endpoint: str

    # Model deployment name
    azure_openai_deployment: str = "gpt-5"

    # Container image
    container_image: str = ""

    # Agent resources
    agent_cpu: str = "1"
    agent_memory: str = "2Gi"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
