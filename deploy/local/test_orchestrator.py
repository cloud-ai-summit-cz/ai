#!/usr/bin/env python3
"""Test script for Research Orchestrator API.

This script tests the Research Orchestrator API by:
1. Checking health status
2. Creating a research session
3. Starting the session and streaming SSE events
4. Displaying the final results

Usage:
    uv run python test_orchestrator.py                     # Use default settings
    uv run python test_orchestrator.py --url http://host:port
    uv run python test_orchestrator.py --query "Custom query"

Requirements:
    - Research Orchestrator running (uv run python -m research_orchestrator.main)
    - Foundry agents provisioned (market-analyst, competitor-analyst, synthesizer)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_QUERY = "Analyze the market opportunity for a new specialty coffee shop in Prague 2, focusing on young professionals and remote workers."


@dataclass
class TestConfig:
    """Test configuration."""

    api_url: str
    query: str
    timeout: float = 120.0
    verbose: bool = False


async def check_health(client: httpx.AsyncClient, config: TestConfig) -> bool:
    """Check API health status.

    Args:
        client: HTTP client.
        config: Test configuration.

    Returns:
        True if healthy, False otherwise.
    """
    console.print("\n[bold blue]1. Health Check[/bold blue]")

    try:
        response = await client.get(f"{config.api_url}/health", timeout=10.0)
        response.raise_for_status()
        health = response.json()

        table = Table(title="Health Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Status", health.get("status", "unknown"))
        table.add_row("Version", health.get("version", "unknown"))
        table.add_row("Foundry Connected", str(health.get("foundry_connected", False)))
        table.add_row("Agents Available", ", ".join(health.get("agents_available", [])))

        console.print(table)

        if not health.get("foundry_connected"):
            console.print("[yellow]⚠ Warning: Foundry not connected. Workflow may fail.[/yellow]")
            return False

        required_agents = {"market-analyst", "competitor-analyst", "synthesizer"}
        available = set(health.get("agents_available", []))
        missing = required_agents - available

        if missing:
            console.print(f"[yellow]⚠ Missing agents: {', '.join(missing)}[/yellow]")
            console.print("[dim]Run provisioning scripts to create missing agents.[/dim]")
            return False

        console.print("[green]✓ All systems healthy[/green]")
        return True

    except httpx.HTTPError as e:
        console.print(f"[red]✗ Health check failed: {e}[/red]")
        return False


async def create_session(client: httpx.AsyncClient, config: TestConfig) -> str | None:
    """Create a research session.

    Args:
        client: HTTP client.
        config: Test configuration.

    Returns:
        Session ID if created, None otherwise.
    """
    console.print("\n[bold blue]2. Create Research Session[/bold blue]")
    console.print(f"[dim]Query: {config.query}[/dim]")

    try:
        response = await client.post(
            f"{config.api_url}/research/sessions",
            json={"query": config.query},
            timeout=10.0,
        )
        response.raise_for_status()
        session = response.json()

        session_id = session.get("session_id")
        console.print(f"[green]✓ Session created: {session_id}[/green]")
        console.print(f"[dim]Status: {session.get('status')}[/dim]")

        return session_id

    except httpx.HTTPError as e:
        console.print(f"[red]✗ Failed to create session: {e}[/red]")
        return None


async def run_session(client: httpx.AsyncClient, config: TestConfig, session_id: str) -> bool:
    """Run a research session and stream SSE events.

    Args:
        client: HTTP client.
        config: Test configuration.
        session_id: The session ID to run.

    Returns:
        True if successful, False otherwise.
    """
    console.print("\n[bold blue]3. Run Research Workflow[/bold blue]")
    console.print("[dim]Streaming SSE events...[/dim]")
    if config.verbose:
        console.print("[dim]Verbose mode: showing detailed event data[/dim]")
    console.print()

    agent_results: dict[str, dict] = {}
    workflow_complete = False
    event_type = ""

    try:
        async with client.stream(
            "POST",
            f"{config.api_url}/research/sessions/{session_id}/start",
            timeout=config.timeout,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                # Parse SSE format
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        _display_event(event_type, data, agent_results, config.verbose)

                        if event_type == "workflow_completed":
                            workflow_complete = True
                        elif event_type == "workflow_failed":
                            console.print(
                                f"[red]✗ Workflow failed: {data.get('data', {}).get('error')}[/red]"
                            )
                            return False
                    except json.JSONDecodeError:
                        pass

        if workflow_complete:
            console.print("\n[green]✓ Workflow completed successfully![/green]")
            await _display_final_results(client, config, session_id)
            return True

        return False

    except httpx.HTTPError as e:
        console.print(f"[red]✗ Workflow execution failed: {e}[/red]")
        return False
    except asyncio.TimeoutError:
        console.print(f"[red]✗ Workflow timed out after {config.timeout}s[/red]")
        return False


def _display_event(event_type: str, data: dict, agent_results: dict[str, dict], verbose: bool = False) -> None:
    """Display an SSE event with formatting.

    Args:
        event_type: The event type.
        data: The event data.
        agent_results: Dictionary to accumulate agent results.
        verbose: Whether to show detailed event data.
    """
    event_data = data.get("data", {})
    timestamp = data.get("timestamp", "")[:19]  # Truncate timestamp

    if event_type == "session_started":
        console.print(f"[cyan]→ Session started[/cyan] [dim]{timestamp}[/dim]")
        mode = event_data.get("mode", "")
        if mode:
            console.print(f"  [dim]Mode: {mode}[/dim]")
        if verbose:
            query = event_data.get("query", "")
            if query:
                console.print(Panel(
                    query,
                    title="[bold]Query[/bold]",
                    border_style="cyan",
                    padding=(0, 1),
                ))

    elif event_type == "agent_started":
        agent = event_data.get("agent", "unknown")
        phase = event_data.get("phase", "orchestration")
        description = event_data.get("description", "")
        tools = event_data.get("available_tools", [])
        console.print(f"[yellow]⚙ {phase}[/yellow] starting [dim]{timestamp}[/dim]")
        if tools:
            console.print(f"  [dim]Available tools: {', '.join(tools)}[/dim]")
        if verbose and description:
            console.print(f"  [dim]Description: {description}[/dim]")

    elif event_type == "agent_thinking":
        # Tool call started by orchestrator
        tool = event_data.get("tool", "unknown")
        call_number = event_data.get("call_number", 1)
        orchestrator_action = event_data.get("orchestrator_action", "")
        args_preview = event_data.get("args_preview", "")
        
        console.print(f"[yellow]🔧 Calling tool:[/yellow] [bold cyan]{tool}[/bold cyan] (call #{call_number}) [dim]{timestamp}[/dim]")
        if verbose and args_preview:
            console.print(f"  [dim]Args: {args_preview[:150]}...[/dim]" if len(args_preview) > 150 else f"  [dim]Args: {args_preview}[/dim]")

    elif event_type == "agent_progress":
        agent = event_data.get("agent", "unknown")
        text = event_data.get("text", "")
        if verbose and text:
            # Show streaming text chunks
            console.print(f"[dim][{agent}][/dim] {text}", end="")
        # In non-verbose mode, we skip these to reduce noise

    elif event_type == "agent_completed":
        # Tool call completed
        tool = event_data.get("tool")
        agent = event_data.get("agent", tool or "unknown")
        time_ms = event_data.get("execution_time_ms", 0)
        call_number = event_data.get("call_number", "")
        result_preview = event_data.get("result_preview", "")
        
        if tool:
            # This is a tool completion
            console.print(
                f"[green]✓ Tool {tool}[/green] (call #{call_number}) completed in {time_ms}ms [dim]{timestamp}[/dim]"
            )
            if verbose and result_preview:
                # Show preview of tool result
                preview_text = result_preview[:300] + "..." if len(result_preview) > 300 else result_preview
                console.print(f"  [dim]Result preview: {preview_text}[/dim]")
        else:
            # Generic agent completion
            console.print(
                f"[green]✓ {agent}[/green] completed in {time_ms}ms [dim]{timestamp}[/dim]"
            )
        
        agent_results[tool or agent] = {"execution_time_ms": time_ms}

    elif event_type == "agent_failed":
        error = event_data.get("error", "Unknown error")
        console.print(f"[red]✗ Agent failed: {error}[/red] [dim]{timestamp}[/dim]")
        if verbose:
            console.print(Panel(
                str(event_data),
                title="[bold red]Error Details[/bold red]",
                border_style="red",
            ))

    elif event_type == "synthesis_started":
        agent = event_data.get("agent", "synthesizer")
        description = event_data.get("description", "")
        console.print(f"[yellow]⚙ {agent}[/yellow] starting synthesis [dim]{timestamp}[/dim]")
        if verbose and description:
            console.print(f"  [dim]Description: {description}[/dim]")

    elif event_type == "synthesis_progress":
        agent = event_data.get("agent", "synthesizer")
        text = event_data.get("text", "")
        if verbose and text:
            # Show streaming synthesis text
            console.print(f"[dim]{text}[/dim]", end="")

    elif event_type == "synthesis_completed":
        time_ms = event_data.get("execution_time_ms", 0)
        tool_calls = event_data.get("tool_calls_made", [])
        agent_counts = event_data.get("agent_call_counts", {})
        
        console.print(f"[green]✓ Orchestrator[/green] completed in {time_ms}ms [dim]{timestamp}[/dim]")
        
        if agent_counts:
            counts_str = ", ".join(f"{k}: {v}" for k, v in agent_counts.items() if v > 0)
            console.print(f"  [dim]Tool calls: {counts_str}[/dim]")

    elif event_type == "workflow_completed":
        total_time = event_data.get("total_time_ms", 0)
        total_calls = event_data.get("total_tool_calls", 0)
        agent_counts = event_data.get("agent_call_counts", {})
        
        # Build summary string
        summary_parts = []
        for agent, count in agent_counts.items():
            if count > 0:
                summary_parts.append(f"{agent}×{count}")
        summary = ", ".join(summary_parts) if summary_parts else f"{total_calls} tool calls"
        
        console.print(
            f"\n[bold green]✓ Workflow complete[/bold green] "
            f"({summary}, {total_time}ms total)"
        )
        if verbose:
            synthesis = event_data.get("synthesis", "")
            if synthesis:
                console.print(Panel(
                    synthesis[:1000] + ("..." if len(synthesis) > 1000 else ""),
                    title="[bold]Synthesis Preview[/bold]",
                    border_style="green",
                ))

    else:
        # Unknown event type - show in verbose mode
        if verbose:
            console.print(f"[dim]Event: {event_type}[/dim] [dim]{timestamp}[/dim]")
            console.print(f"  [dim]Data: {json.dumps(event_data, indent=2)[:500]}[/dim]")


async def _display_final_results(
    client: httpx.AsyncClient, config: TestConfig, session_id: str
) -> None:
    """Display final session results.

    Args:
        client: HTTP client.
        config: Test configuration.
        session_id: The session ID.
    """
    console.print("\n[bold blue]4. Final Results[/bold blue]")

    try:
        response = await client.get(
            f"{config.api_url}/research/sessions/{session_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        session = response.json()

        # Display agent results summary
        table = Table(title="Agent Results")
        table.add_column("Agent", style="cyan")
        table.add_column("Time (ms)", style="yellow", justify="right")

        for result in session.get("agent_results", []):
            table.add_row(
                result.get("agent_name", "unknown"),
                str(result.get("execution_time_ms", 0)),
            )

        console.print(table)

        # Display final synthesis
        synthesis = session.get("final_synthesis")
        if synthesis:
            console.print(Panel(
                synthesis[:2000] + ("..." if len(synthesis) > 2000 else ""),
                title="[bold]Final Synthesis[/bold]",
                border_style="green",
            ))

    except httpx.HTTPError as e:
        console.print(f"[red]Failed to fetch final results: {e}[/red]")


async def main() -> int:
    """Main test runner.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Test the Research Orchestrator API"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Research query to test with",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Workflow timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--health-only",
        action="store_true",
        help="Only run health check",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed SSE event data including messages and context",
    )
    args = parser.parse_args()

    # Load environment
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    config = TestConfig(
        api_url=args.url.rstrip("/"),
        query=args.query,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    console.print(Panel.fit(
        f"[bold]Research Orchestrator Test[/bold]\n"
        f"API URL: {config.api_url}\n"
        f"Timeout: {config.timeout}s",
        border_style="blue",
    ))

    async with httpx.AsyncClient() as client:
        # Health check
        healthy = await check_health(client, config)

        if args.health_only:
            return 0 if healthy else 1

        if not healthy:
            console.print("\n[yellow]Proceeding despite health warnings...[/yellow]")

        # Create session
        session_id = await create_session(client, config)
        if not session_id:
            return 1

        # Run workflow
        success = await run_session(client, config, session_id)

        if success:
            console.print("\n[bold green]✓ All tests passed![/bold green]")
            return 0
        else:
            console.print("\n[bold red]✗ Tests failed[/bold red]")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
