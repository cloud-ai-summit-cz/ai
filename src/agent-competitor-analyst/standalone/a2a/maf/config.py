"""Configuration for standalone Competitor Analyst A2A Agent."""

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

    # Azure OpenAI Configuration
    azure_openai_endpoint: str
    model_deployment_name: str = "gpt-5"
    azure_openai_api_version: str = "preview"

    @property
    def azure_openai_base_url(self) -> str:
        """Get the base URL for the Responses API.
        
        For cognitiveservices.azure.com endpoints, we need to explicitly
        set the /openai/v1/ path for the Responses API.
        """
        endpoint = self.azure_openai_endpoint.rstrip("/")
        return f"{endpoint}/openai/v1/"

    # MCP Business Registry Configuration (for competitor data)
    mcp_business_registry_url: str
    mcp_business_registry_api_key: str

    # MCP Scratchpad Configuration (for inter-agent collaboration)
    mcp_scratchpad_url: str
    mcp_scratchpad_api_key: str

    # A2A Server Configuration
    a2a_server_host: str = "0.0.0.0"
    a2a_server_port: int = 8021
    a2a_public_host: str = "localhost"  # Host used in AgentCard URL (reachable address)
    a2a_api_key: str | None = None  # API key for authentication (None = no auth)
    a2a_agent_name: str = "Competitor Analyst Agent"
    a2a_agent_description: str = (
        "Competitive landscape analysis specialist for Cofilot's coffee business expansion. "
        "Provides competitor identification, profiling, positioning analysis, "
        "and competitive threat assessment for specialty coffee markets in Brno and Vienna."
    )
    a2a_agent_version: str = "1.0.0"

    @property
    def a2a_public_url(self) -> str:
        """Get the public URL for the A2A agent.
        
        Intelligently determines the URL based on the public host:
        - If host already has a scheme (http:// or https://), use it as-is
        - localhost/127.0.0.1: defaults to http:// with port
        - Everything else: defaults to https:// without port
        """
        host = self.a2a_public_host
        
        # If already has scheme, use as-is (just ensure trailing slash)
        if host.startswith("http://") or host.startswith("https://"):
            return host.rstrip("/") + "/"
        
        # Local development - use HTTP with port
        if host in ("localhost", "127.0.0.1"):
            return f"http://{host}:{self.a2a_server_port}/"
        
        # Everything else (cloud, production) - use HTTPS without port
        return f"https://{host}/"

    # Prompts directory - can be overridden for container deployment
    prompts_dir_override: str | None = None

    @property
    def prompts_dir(self) -> Path:
        """Get the prompts directory path.
        
        In container: use PROMPTS_DIR_OVERRIDE env var pointing to /app/prompts
        Locally: resolve relative to parent directories
        """
        if self.prompts_dir_override:
            return Path(self.prompts_dir_override)
        return Path(__file__).parent.parent.parent.parent / "prompts"

    def get_system_prompt(self) -> str:
        """Load the system prompt.

        Returns:
            The system prompt content.
        """
        prompt_path = self.prompts_dir / "system_prompt.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"System prompt not found: {prompt_path}")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
