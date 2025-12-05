"""Configuration management for Research Orchestrator."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Well-known agent names (hardcoded, must match provisioned agents in Foundry)
MARKET_ANALYST_AGENT_NAME = "market-analyst"
COMPETITOR_ANALYST_AGENT_NAME = "competitor-analyst"
LOCATION_SCOUT_AGENT_NAME = "location-scout"
FINANCE_ANALYST_AGENT_NAME = "finance-analyst"
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

    # MCP Demographics configuration (ADR-006: orchestrator-managed)
    mcp_demographics_url: str = Field(
        default="",
        alias="MCP_DEMOGRAPHICS_URL",
        description="URL to the MCP Demographics server",
    )
    mcp_demographics_api_key: str = Field(
        default="",
        alias="MCP_DEMOGRAPHICS_API_KEY",
        description="API key for MCP Demographics authentication",
    )

    # MCP Business Registry configuration (ADR-006: orchestrator-managed)
    mcp_business_registry_url: str = Field(
        default="",
        alias="MCP_BUSINESS_REGISTRY_URL",
        description="URL to the MCP Business Registry server",
    )
    mcp_business_registry_api_key: str = Field(
        default="",
        alias="MCP_BUSINESS_REGISTRY_API_KEY",
        description="API key for MCP Business Registry authentication",
    )

    # MCP Government Data configuration (ADR-006: orchestrator-managed)
    mcp_government_data_url: str = Field(
        default="",
        alias="MCP_GOVERNMENT_DATA_URL",
        description="URL to the MCP Government Data server",
    )
    mcp_government_data_api_key: str = Field(
        default="",
        alias="MCP_GOVERNMENT_DATA_API_KEY",
        description="API key for MCP Government Data authentication",
    )

    # MCP Real Estate configuration (ADR-006: orchestrator-managed)
    mcp_real_estate_url: str = Field(
        default="",
        alias="MCP_REAL_ESTATE_URL",
        description="URL to the MCP Real Estate server",
    )
    mcp_real_estate_api_key: str = Field(
        default="",
        alias="MCP_REAL_ESTATE_API_KEY",
        description="API key for MCP Real Estate authentication",
    )

    # MCP Calculator configuration (ADR-006: orchestrator-managed)
    mcp_calculator_url: str = Field(
        default="",
        alias="MCP_CALCULATOR_URL",
        description="URL to the MCP Calculator server",
    )
    mcp_calculator_api_key: str = Field(
        default="",
        alias="MCP_CALCULATOR_API_KEY",
        description="API key for MCP Calculator authentication",
    )

    # A2A Market Analyst Agent configuration
    a2a_market_analyst_url: str = Field(
        default="",
        alias="A2A_MARKET_ANALYST_URL",
        description="URL to the Market Analyst A2A agent endpoint (e.g., https://apim-xxx/market-analyst)",
    )
    a2a_market_analyst_api_key: str = Field(
        default="",
        alias="A2A_MARKET_ANALYST_API_KEY",
        description="API key for Market Analyst A2A authentication",
    )

    # A2A Competitor Analyst Agent configuration
    a2a_competitor_analyst_url: str = Field(
        default="",
        alias="A2A_COMPETITOR_ANALYST_URL",
        description="URL to the Competitor Analyst A2A agent endpoint (e.g., https://apim-xxx/competitor-analyst)",
    )
    a2a_competitor_analyst_api_key: str = Field(
        default="",
        alias="A2A_COMPETITOR_ANALYST_API_KEY",
        description="API key for Competitor Analyst A2A authentication",
    )

    # A2A Finance Analyst Agent configuration
    a2a_finance_analyst_url: str = Field(
        default="",
        alias="A2A_FINANCE_ANALYST_URL",
        description="URL to the Finance Analyst A2A agent endpoint (e.g., https://apim-xxx/finance-analyst)",
    )
    a2a_finance_analyst_api_key: str = Field(
        default="",
        alias="A2A_FINANCE_ANALYST_API_KEY",
        description="API key for Finance Analyst A2A authentication",
    )

    # A2A Location Scout Agent configuration
    a2a_location_scout_url: str = Field(
        default="",
        alias="A2A_LOCATION_SCOUT_URL",
        description="URL to the Location Scout A2A agent endpoint (e.g., https://apim-xxx/location-scout)",
    )
    a2a_location_scout_api_key: str = Field(
        default="",
        alias="A2A_LOCATION_SCOUT_API_KEY",
        description="API key for Location Scout A2A authentication",
    )

    # A2A Synthesizer Agent configuration
    a2a_synthesizer_url: str = Field(
        default="",
        alias="A2A_SYNTHESIZER_URL",
        description="URL to the Synthesizer A2A agent endpoint (e.g., https://apim-xxx/synthesizer)",
    )
    a2a_synthesizer_api_key: str = Field(
        default="",
        alias="A2A_SYNTHESIZER_API_KEY",
        description="API key for Synthesizer A2A authentication",
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
    api_reload: bool = Field(default=False, description="Enable auto-reload for development")

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
    def mcp_demographics_enabled(self) -> bool:
        """Check if MCP Demographics is configured (ADR-006)."""
        return bool(self.mcp_demographics_url and self.mcp_demographics_api_key)

    @property
    def mcp_business_registry_enabled(self) -> bool:
        """Check if MCP Business Registry is configured (ADR-006)."""
        return bool(self.mcp_business_registry_url and self.mcp_business_registry_api_key)

    @property
    def mcp_government_data_enabled(self) -> bool:
        """Check if MCP Government Data is configured (ADR-006)."""
        return bool(self.mcp_government_data_url and self.mcp_government_data_api_key)

    @property
    def mcp_real_estate_enabled(self) -> bool:
        """Check if MCP Real Estate is configured (ADR-006)."""
        return bool(self.mcp_real_estate_url and self.mcp_real_estate_api_key)

    @property
    def mcp_calculator_enabled(self) -> bool:
        """Check if MCP Calculator is configured (ADR-006)."""
        return bool(self.mcp_calculator_url and self.mcp_calculator_api_key)

    @property
    def a2a_market_analyst_enabled(self) -> bool:
        """Check if Market Analyst A2A agent is configured."""
        return bool(self.a2a_market_analyst_url and self.a2a_market_analyst_api_key)

    @property
    def a2a_competitor_analyst_enabled(self) -> bool:
        """Check if Competitor Analyst A2A agent is configured."""
        return bool(self.a2a_competitor_analyst_url and self.a2a_competitor_analyst_api_key)

    @property
    def a2a_finance_analyst_enabled(self) -> bool:
        """Check if Finance Analyst A2A agent is configured."""
        return bool(self.a2a_finance_analyst_url and self.a2a_finance_analyst_api_key)

    @property
    def a2a_location_scout_enabled(self) -> bool:
        """Check if Location Scout A2A agent is configured."""
        return bool(self.a2a_location_scout_url and self.a2a_location_scout_api_key)

    @property
    def a2a_synthesizer_enabled(self) -> bool:
        """Check if Synthesizer A2A agent is configured."""
        return bool(self.a2a_synthesizer_url and self.a2a_synthesizer_api_key)

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
