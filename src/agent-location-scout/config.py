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

    # Azure AI Foundry connection
    azure_ai_foundry_endpoint: str

    # Azure OpenAI (for LangGraph agent)
    azure_openai_endpoint: str | None = None

    # Model deployment
    azure_ai_model_deployment_name: str = "gpt-4o"

    # Container image (for hosted agent deployment)
    container_image: str | None = None

    # Agent resources
    agent_cpu: str = "1"
    agent_memory: str = "2Gi"

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
