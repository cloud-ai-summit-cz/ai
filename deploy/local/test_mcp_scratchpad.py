#!/usr/bin/env python3
"""Test script for MCP Scratchpad integration with Research Orchestrator.

This script tests the MCP Scratchpad server connectivity and basic operations
using the Microsoft Agent Framework's MCPStreamableHTTPTool.

Usage:
    uv run python test_mcp_scratchpad.py                     # Use default (local) settings
    uv run python test_mcp_scratchpad.py --url https://ca-mcp-scratchpad...  # Remote
    uv run python test_mcp_scratchpad.py --api-key YOUR_KEY  # With auth

Requirements:
    - MCP Scratchpad server running (locally or in Azure Container Apps)
    - agent-framework package installed
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Default settings for local development
DEFAULT_MCP_URL = "http://localhost:8010/mcp"
DEFAULT_HEALTH_URL = "http://localhost:8010/health"


async def test_health_endpoint(health_url: str, api_key: str | None = None) -> bool:
    """Test the MCP server health endpoint.

    Args:
        health_url: URL to the health endpoint.
        api_key: Optional API key for authentication.

    Returns:
        True if healthy, False otherwise.
    """
    console.print("\n[bold blue]1. Testing Health Endpoint[/bold blue]")
    console.print(f"[dim]URL: {health_url}[/dim]")

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            health = response.json()

            console.print(f"[green]✓ Health endpoint returned: {health}[/green]")
            return True

    except httpx.HTTPError as e:
        console.print(f"[red]✗ Health check failed: {e}[/red]")
        return False


async def test_mcp_connection(mcp_url: str, api_key: str | None = None) -> bool:
    """Test basic MCP connection using MCPStreamableHTTPTool.

    Args:
        mcp_url: URL to the MCP endpoint (e.g., http://localhost:8010/mcp).
        api_key: Optional API key for authentication.

    Returns:
        True if connection successful, False otherwise.
    """
    console.print("\n[bold blue]2. Testing MCP Connection (MCPStreamableHTTPTool)[/bold blue]")
    console.print(f"[dim]URL: {mcp_url}[/dim]")

    try:
        from agent_framework import MCPStreamableHTTPTool
    except ImportError:
        console.print("[red]✗ Failed to import MCPStreamableHTTPTool from agent_framework[/red]")
        console.print("[yellow]Make sure agent-framework is installed with MCP support[/yellow]")
        return False

    headers = {}
    if api_key:
        # FastMCP StaticTokenVerifier expects: Authorization: Bearer <token>
        headers["Authorization"] = f"Bearer {api_key}"
        console.print(f"[dim]Auth header: Authorization: Bearer {api_key[:10]}...[/dim]")

    try:
        async with MCPStreamableHTTPTool(
            name="scratchpad",
            url=mcp_url,
            headers=headers if headers else None,
        ) as mcp_tool:
            console.print("[green]✓ MCP connection established[/green]")

            # List available tools from the MCP server
            # The tools are exposed via the .functions property
            tools = mcp_tool.functions
            
            table = Table(title="Available MCP Tools")
            table.add_column("Tool Name", style="cyan")
            table.add_column("Description", style="dim")

            for tool in tools:
                tool_name = getattr(tool, 'name', str(tool))
                tool_desc = getattr(tool, 'description', '')
                if len(tool_desc) > 60:
                    tool_desc = tool_desc[:60] + "..."
                table.add_row(tool_name, tool_desc)

            console.print(table)
            console.print(f"[green]✓ Found {len(tools)} tools[/green]")
            return True

    except Exception as e:
        console.print(f"[red]✗ MCP connection failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


async def test_tool_execution(mcp_url: str, api_key: str | None = None) -> bool:
    """Test executing MCP tools (write and read operations).

    Args:
        mcp_url: URL to the MCP endpoint.
        api_key: Optional API key for authentication.

    Returns:
        True if tests pass, False otherwise.
    """
    console.print("\n[bold blue]3. Testing Tool Execution[/bold blue]")

    try:
        from agent_framework import MCPStreamableHTTPTool
    except ImportError:
        console.print("[red]✗ MCPStreamableHTTPTool not available[/red]")
        return False

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with MCPStreamableHTTPTool(
            name="scratchpad",
            url=mcp_url,
            headers=headers if headers else None,
        ) as mcp_tool:
            # Get the tools via .functions property
            tools = mcp_tool.functions
            tool_map = {getattr(t, 'name', ''): t for t in tools}

            console.print(f"[dim]Available tools: {list(tool_map.keys())}[/dim]")

            # Test write_section
            console.print("[dim]Testing write_section...[/dim]")
            if 'write_section' in tool_map:
                write_tool = tool_map['write_section']
                # The tool is a callable - invoke it
                result = await write_tool.invoke(
                    section_name="test_section",
                    content="This is a test from the MCP integration test script.",
                )
                console.print(f"[green]✓ write_section: {result}[/green]")
            else:
                console.print("[yellow]⚠ write_section tool not found[/yellow]")

            # Test read_section
            console.print("[dim]Testing read_section...[/dim]")
            if 'read_section' in tool_map:
                read_tool = tool_map['read_section']
                result = await read_tool.invoke(section_name="test_section")
                console.print(f"[green]✓ read_section: {result}[/green]")
            else:
                console.print("[yellow]⚠ read_section tool not found[/yellow]")

            # Test list_sections
            console.print("[dim]Testing list_sections...[/dim]")
            if 'list_sections' in tool_map:
                list_tool = tool_map['list_sections']
                result = await list_tool.invoke()
                console.print(f"[green]✓ list_sections: {result}[/green]")
            else:
                console.print("[yellow]⚠ list_sections tool not found[/yellow]")

            console.print("[green]✓ Tool execution tests passed[/green]")
            return True

    except Exception as e:
        console.print(f"[red]✗ Tool execution failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


async def test_with_chat_agent(mcp_url: str, api_key: str | None = None) -> bool:
    """Test MCP integration with ChatAgent (requires Azure AI config).

    Args:
        mcp_url: URL to the MCP endpoint.
        api_key: Optional API key for authentication.

    Returns:
        True if test passes, False otherwise.
    """
    console.print("\n[bold blue]4. Testing ChatAgent Integration (Optional)[/bold blue]")

    import os
    foundry_endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not foundry_endpoint or not model_deployment:
        console.print("[yellow]⚠ Skipping ChatAgent test - AZURE_AI_FOUNDRY_ENDPOINT or MODEL_DEPLOYMENT_NAME not set[/yellow]")
        return True  # Not a failure, just skipped

    try:
        from agent_framework import ChatAgent, MCPStreamableHTTPTool
        from agent_framework_azure_ai import AzureAIAgentClient
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as e:
        console.print(f"[yellow]⚠ Skipping ChatAgent test - missing dependencies: {e}[/yellow]")
        return True

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    credential = None
    try:
        credential = DefaultAzureCredential()

        async with MCPStreamableHTTPTool(
            name="scratchpad",
            url=mcp_url,
            headers=headers if headers else None,
        ) as mcp_tool:
            client = AzureAIAgentClient(
                project_endpoint=foundry_endpoint,
                model_deployment_name=model_deployment,
                async_credential=credential,
            )

            agent = ChatAgent(
                chat_client=client,
                name="test-agent",
                instructions="You are a test agent with access to a scratchpad tool.",
                tools=[mcp_tool],
            )

            console.print("[dim]Asking agent to use scratchpad...[/dim]")
            thread = agent.get_new_thread()
            response = ""
            async for update in agent.run_stream(
                "Please write 'Hello from ChatAgent test!' to the scratchpad section named 'agent_test', then read it back to confirm.",
                thread=thread,
            ):
                if update.text:
                    response += update.text

            console.print(f"[green]✓ ChatAgent response: {response[:200]}...[/green]")
            return True

    except Exception as e:
        console.print(f"[red]✗ ChatAgent test failed: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False
    finally:
        if credential:
            await credential.close()


async def main() -> int:
    """Main test runner.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Test MCP Scratchpad integration"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_MCP_URL,
        help=f"MCP server URL (default: {DEFAULT_MCP_URL})",
    )
    parser.add_argument(
        "--api-key",
        help="API key for MCP server authentication",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Only run health check",
    )
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip ChatAgent integration test",
    )
    args = parser.parse_args()

    # Load environment from local .env
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        console.print(f"[dim]Loaded environment from {env_file}[/dim]")

    # Also check for API key in environment if not provided
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.getenv("MCP_SCRATCHPAD_API_KEY")
        if api_key:
            console.print("[dim]Using MCP_SCRATCHPAD_API_KEY from environment[/dim]")

    # Derive health URL from MCP URL
    mcp_url = args.url.rstrip("/")
    if mcp_url.endswith("/mcp"):
        health_url = mcp_url.rsplit("/mcp", 1)[0] + "/health"
    else:
        health_url = mcp_url + "/health"
        mcp_url = mcp_url + "/mcp"

    console.print(Panel.fit(
        f"[bold]MCP Scratchpad Integration Test[/bold]\n"
        f"MCP URL: {mcp_url}\n"
        f"Health URL: {health_url}\n"
        f"Auth: {'Yes' if api_key else 'No'}",
        border_style="blue",
    ))

    all_passed = True

    # Test 1: Health endpoint
    if not await test_health_endpoint(health_url, api_key):
        all_passed = False
        if args.health_only:
            return 1

    if args.health_only:
        return 0

    # Test 2: MCP connection
    if not await test_mcp_connection(mcp_url, api_key):
        all_passed = False

    # Test 3: Tool execution
    if not await test_tool_execution(mcp_url, api_key):
        all_passed = False

    # Test 4: ChatAgent integration (optional)
    if not args.skip_agent:
        if not await test_with_chat_agent(mcp_url, api_key):
            all_passed = False

    if all_passed:
        console.print("\n[bold green]✓ All tests passed![/bold green]")
        return 0
    else:
        console.print("\n[bold red]✗ Some tests failed[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
