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

    # MCP Scratchpad configuration
    mcp_scratchpad_url: str = Field(
        default="",
        alias="MCP_SCRATCHPAD_URL",
        description="URL to the MCP Scratchpad server (e.g., https://ca-mcp-scratchpad.../mcp)",
    )
    mcp_scratchpad_api_key: str = Field(
        default="",
        alias="MCP_SCRATCHPAD_API_KEY",
        description="API key for MCP Scratchpad authentication",
    )

    # Application Insights / Log Analytics configuration (ADR-005)
    log_analytics_workspace_id: str = Field(
        default="",
        alias="LOG_ANALYTICS_WORKSPACE_ID",
        description="Log Analytics Workspace ID (GUID) for querying App Insights traces",
    )
    trace_polling_enabled: bool = Field(
        default=True,
        alias="TRACE_POLLING_ENABLED",
        description="Enable App Insights trace polling for real-time SSE events",
    )
    trace_polling_interval_seconds: float = Field(
        default=2.0,
        alias="TRACE_POLLING_INTERVAL_SECONDS",
        description="How often to poll App Insights for new traces",
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

    @property
    def mcp_scratchpad_enabled(self) -> bool:
        """Check if MCP Scratchpad is configured."""
        return bool(self.mcp_scratchpad_url and self.mcp_scratchpad_api_key)

    @property
    def trace_polling_configured(self) -> bool:
        """Check if App Insights trace polling is configured and enabled."""
        return bool(
            self.trace_polling_enabled and 
            self.log_analytics_workspace_id
        )

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
