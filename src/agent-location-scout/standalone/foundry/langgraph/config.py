"""Configuration management for Location Scout hosted agent (LangGraph)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Agent identity
    agent_name: str = "location-scout"

    # Azure subscription/resource group (for ARM REST API calls)
    azure_subscription_id: str | None = None
    azure_resource_group: str = "rg-agentic-poc"

    # Azure AI Foundry connection
    azure_ai_foundry_endpoint: str

    # Azure OpenAI (for LangGraph agent)
    azure_openai_endpoint: str | None = None

    # Model deployment name
    azure_openai_deployment: str = "gpt-5"
    model_name: str | None = None  # Alternative env var name

    # Container image (for hosted agent deployment)
    container_image: str = ""

    # Agent resources
    agent_cpu: str = "1"
    agent_memory: str = "2Gi"

    @property
    def effective_model_deployment(self) -> str:
        """Get the model deployment name from either env var."""
        return self.model_name or self.azure_openai_deployment

    @property
    def prompts_dir(self) -> Path:
        """Get the prompts directory path (in parent agent folder)."""
        return Path(__file__).parent.parent.parent.parent / "prompts"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
