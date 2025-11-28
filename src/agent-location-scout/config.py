"""Configuration management for Location Scout agent."""

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
    # Can be set via AZURE_OPENAI_DEPLOYMENT or MODEL_NAME env vars
    azure_openai_deployment: str = "gpt-5"
    model_name: str | None = None  # Alternative env var name used by provision.py

    # Container image (for hosted agent deployment)
    # Set via CONTAINER_IMAGE env var or use terraform output: agent_location_scout_image
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
        """Get the prompts directory path."""
        return Path(__file__).parent / "prompts"

    def get_prompt(self, prompt_name: str = "system_prompt") -> str:
        """Load a prompt file.

        Args:
            prompt_name: The prompt file name (without .jinja2 extension)

        Returns:
            The prompt content as a string.

        Raises:
            FileNotFoundError: If the prompt file doesn't exist.
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.jinja2"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
