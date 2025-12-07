"""Configuration management for Market Analyst agent."""

from functools import lru_cache
from pathlib import Path

from jinja2 import Template
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

    # Model deployment
    model_deployment_name: str = "gpt-5"

    # MCP Server endpoints (for fixed tool provisioning)
    # These are configured at agent creation time for Foundry UI visibility
    mcp_demographics_url: str = "http://localhost:8014/mcp"
    mcp_scratchpad_url: str = "http://localhost:8010/mcp"
    mcp_web_search_url: str = "http://localhost:8011/mcp"

    # MCP Auth token (shared across MCP servers)
    mcp_auth_token: str = "dev-mcp-auth-key"

    @property
    def prompts_dir(self) -> Path:
        """Get the prompts directory path."""
        return Path(__file__).parent / "prompts"

    def get_prompt(self, prompt_name: str = "system_prompt", language: str = "cs") -> str:
        """Load and render a prompt template.

        Args:
            prompt_name: The prompt file name (without .jinja2 extension)
            language: The language code ('cs' for Czech, 'en' for English)

        Returns:
            The rendered prompt content as a string.

        Raises:
            FileNotFoundError: If the prompt file doesn't exist.
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.jinja2"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        template = Template(prompt_path.read_text(encoding="utf-8"))
        return template.render(language=language)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
