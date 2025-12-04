"""Entry point for the Location Scout hosted agent.

This module starts the agent using the Azure AI AgentServer adapter,
which exposes the LangGraph agent as a Foundry-compatible HTTP service.
"""

import os
import logging

from dotenv import load_dotenv

# Load environment variables before other imports
load_dotenv()

from azure.ai.agentserver.langgraph import from_langgraph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Optional: Configure Azure Monitor if connection string is set
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(enable_live_metrics=True, logger_name="agent-location-scout")
    logger.info("Azure Monitor telemetry configured")


def main() -> None:
    """Start the hosted agent server."""
    logger.info("Starting Location Scout agent...")
    
    # Import here to ensure env vars are loaded
    from agent import build_agent
    
    try:
        agent = build_agent()
        logger.info("Agent built successfully, starting server on port 8010...")
        
        # The adapter handles all protocol translation and HTTP serving
        # Default port is 8010
        from_langgraph(agent).run()
        
    except Exception:
        logger.exception("Failed to start Location Scout agent")
        raise


if __name__ == "__main__":
    main()
