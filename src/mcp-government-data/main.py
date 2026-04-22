"""Entry point for MCP Government Data server."""

import logging
import os

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Configure Azure Monitor telemetry if connection string is set
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if connection_string:
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        configure_azure_monitor(
            connection_string=connection_string,
            service_name="mcp-government-data",
            enable_live_metrics=True,
        )
        FastAPIInstrumentor.instrument()
        logger.info("Azure Monitor telemetry configured for mcp-government-data")
    except ImportError as e:
        logger.warning(f"Failed to configure telemetry - missing dependency: {e}")
else:
    logger.info("APPLICATIONINSIGHTS_CONNECTION_STRING not set - tracing disabled")

from config import settings
from server import mcp

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
