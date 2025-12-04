"""Simple MCP client test script for MCP server.

DESCRIPTION:
    This sample demonstrates how to interact with MCP (Model Context Protocol)
    tools using the low-level MCP client library.

USAGE:
    python mcp_test_client.py

    Before running the sample:
    pip install mcp python-dotenv

    Set these environment variables (or use defaults):
    - MCP_SERVER_URL: The MCP server URL
    - MCP_API_KEY: The API key for authentication
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
mcp_server_url = os.getenv(
    "MCP_SERVER_URL",
    "https://mcp-invoice-data.bluetree-fdff5920.eastus2.azurecontainerapps.io/mcp",
)
api_key = os.getenv("MCP_API_KEY", "dev-invoice-data-key")


async def main():
    """Main function to test MCP client connection and tool discovery."""
    logger.info(f"Connecting to MCP server: {mcp_server_url}")

    async with (
        streamablehttp_client(
            url=mcp_server_url,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as (read_stream, write_stream, _),
        ClientSession(read_stream, write_stream) as session,
    ):
        # Initialize the connection
        await session.initialize()
        logger.info("MCP session initialized successfully")

        # List available tools
        tools = await session.list_tools()
        print(f"\n{'='*60}")
        print(f"Available tools: {[tool.name for tool in tools.tools]}")
        print(f"{'='*60}\n")

        # For each tool, print its details
        for tool in tools.tools:
            print(f"Tool Name: {tool.name}")
            print(f"  Description: {tool.description}")
            print(f"  Input Schema: {tool.inputSchema}")
            print()

        # Example: Run the code interpreter tool if available
        tool_names = [tool.name for tool in tools.tools]
        
        # Test check_po tool
        if "check_po" in tool_names:
            print("\n--- Testing check_po tool ---")
            result = await session.call_tool(
                name="check_po",
                arguments={"po_number": "PO-534"},
            )
            print(f"check_po result: {result.content}")

        # # Test get_invoice tool
        # if "get_invoice" in tool_names:
        #     print("\n--- Testing get_invoice tool ---")
        #     result = await session.call_tool(
        #         name="get_invoice",
        #         arguments={"id": "INV-2024-0001"},
        #     )
        #     print(f"get_invoice result: {result.content}")

        # # Test get_po tool
        # if "get_po" in tool_names:
        #     print("\n--- Testing get_po tool ---")
        #     result = await session.call_tool(
        #         name="get_po",
        #         arguments={"po_number": "PO-2024-001"},
        #     )
        #     print(f"get_po result: {result.content}")

        logger.info("MCP client test completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
