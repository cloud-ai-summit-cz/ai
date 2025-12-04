"""Entry point for the Market Analyst A2A Agent.

This module provides the main entry point for running the Market Analyst
agent as a standalone A2A service.
"""

import logging
import sys

import uvicorn

from a2a_server import build_app
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Market Analyst A2A server."""
    settings = get_settings()
    host = settings.a2a_server_host
    port = settings.a2a_server_port

    logger.info("Starting Market Analyst A2A Agent")
    logger.info(f"  Name: {settings.a2a_agent_name}")
    logger.info(f"  Bind: {host}:{port}")
    logger.info(f"  Public URL: http://{settings.a2a_public_host}:{port}/")
    logger.info(f"  Model: {settings.model_deployment_name}")
    logger.info(
        f"  Agent Card: http://{settings.a2a_public_host}:{port}/.well-known/agent-card.json"
    )

    # Build the app with the configured port
    app = build_app(port)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
