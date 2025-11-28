"""Entry point for MCP Scratchpad server."""

from mcp_scratchpad.config import settings
from mcp_scratchpad.server import mcp

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )
