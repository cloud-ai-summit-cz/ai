"""Entry point for MCP Scratchpad server."""

from config import settings
from server import mcp

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
