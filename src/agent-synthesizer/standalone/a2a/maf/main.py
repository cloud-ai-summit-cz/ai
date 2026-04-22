"""Entry point for the Synthesizer A2A Agent.

This module provides the main entry point for running the Synthesizer
agent as a standalone A2A service.
"""

import logging
import sys

import uvicorn

from a2a_server import build_app
from config import get_settings

# Configure logging - set up root logger to capture all modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Override any existing configuration
)

# Explicitly set log levels for our modules
logging.getLogger("agent").setLevel(logging.INFO)
logging.getLogger("a2a_server").setLevel(logging.INFO)
logging.getLogger("config").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Synthesizer A2A server."""
    settings = get_settings()
    host = settings.a2a_server_host
    port = settings.a2a_server_port
    public_url = settings.a2a_public_url

    logger.info("Starting Synthesizer A2A Agent")
    logger.info(f"  Name: {settings.a2a_agent_name}")
    logger.info(f"  Bind: {host}:{port}")
    logger.info(f"  Public URL: {public_url}")
    logger.info(f"  Model: {settings.model_deployment_name}")
    logger.info(f"  Agent Card: {public_url}.well-known/agent-card.json")
    if settings.a2a_api_key:
        logger.info("  Authentication: API Key required")
    else:
        logger.warning("  Authentication: DISABLED (open access)")

    # Build the app with the configured port
    app = build_app(port)

    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
