"""Entry point for MCP Scratchpad server."""

import logging

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from config import settings
from server import mcp

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
