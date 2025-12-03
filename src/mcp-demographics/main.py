"""Entry point for MCP Demographics server."""

import logging

from config import settings

# Configure logging
log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Optional: Azure Monitor telemetry
try:
    import os

    if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor()
        logger.info("Azure Monitor telemetry enabled")
except ImportError:
    pass


def main() -> None:
    """Run the MCP Demographics server."""
    from server import mcp

    logger.info(f"Starting MCP Demographics server on {settings.host}:{settings.port}")
    mcp.run(transport="streamable-http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
