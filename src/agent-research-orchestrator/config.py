"""Configuration management for Research Orchestrator."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Well-known agent names (hardcoded, must match provisioned agents in Foundry)
MARKET_ANALYST_AGENT_NAME = "market-analyst"
COMPETITOR_ANALYST_AGENT_NAME = "competitor-analyst"
SYNTHESIZER_AGENT_NAME = "synthesizer"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure AI Foundry connection
    azure_ai_foundry_endpoint: str = Field(
        alias="AZURE_AI_FOUNDRY_ENDPOINT",
        description="Azure AI Foundry project endpoint",
    )

    # Model deployment (used for agent connections)
    model_deployment_name: str = Field(
        alias="MODEL_DEPLOYMENT_NAME",
        description="Model deployment name in Azure AI Foundry",
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable auto-reload for development")

    # Timeouts
    agent_timeout_seconds: int = Field(
        default=60,
        description="Timeout for individual agent invocations",
    )
    workflow_timeout_seconds: int = Field(
        default=300,
        description="Total workflow timeout",
    )

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
