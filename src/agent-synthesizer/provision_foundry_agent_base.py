"""Provision Synthesizer as a prompt-only agent in Azure AI Foundry.

This creates a "base" agent with just the system prompt - no MCP tools.
The research orchestrator injects MCP tools at runtime for SSE streaming.

MCP tools injected by orchestrator:
- mcp-scratchpad: Session-scoped shared memory (reads other agents' work)
- mcp-calculator: Financial calculations

Usage:
    uv run python provision_foundry_agent_base.py create
    uv run python provision_foundry_agent_base.py list
    uv run python provision_foundry_agent_base.py destroy
"""

import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.table import Table

from config import get_settings

console = Console(force_terminal=True)

AGENT_NAME = "synthesizer"
AGENT_DISPLAY_NAME = "Synthesizer"


def get_client() -> AIProjectClient:
    """Create AI Project client with default credentials."""
    settings = get_settings()
    return AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=settings.azure_ai_foundry_endpoint,
    )


def get_instructions() -> str:
    """Load the system prompt from markdown file."""
    prompt_path = Path(__file__).parent / "prompts" / "system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def create_agent() -> None:
    """Create the agent in AI Foundry (idempotent)."""
    console.print(f"[bold blue]Creating {AGENT_DISPLAY_NAME} Agent[/bold blue]\n")

    settings = get_settings()
    client = get_client()

    with client:
        # Delete existing agent if found (idempotent)
        with console.status("Checking for existing agent..."):
            existing_agents = list(client.agents.list())
            existing = next((a for a in existing_agents if a.name == AGENT_NAME), None)

        if existing:
            console.print("[yellow]Found existing agent, deleting...[/yellow]")
            with console.status(f"Deleting existing {AGENT_NAME}..."):
                try:
                    client.agents.delete(agent_name=AGENT_NAME)
                    console.print(f"[green]✓[/green] Deleted existing [dim]{AGENT_NAME}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not delete {AGENT_NAME}: {e}[/yellow]")

        # Create agent
        with console.status(f"Creating {AGENT_DISPLAY_NAME}..."):
            instructions = get_instructions()

            agent_def = PromptAgentDefinition(
                model=settings.model_deployment_name,
                instructions=instructions,
                tools=[],  # No tools - orchestrator injects them
            )

            client.agents.create(
                name=AGENT_NAME,
                definition=agent_def,
                description=AGENT_DISPLAY_NAME,
            )

            console.print(
                f"[green]✓[/green] Created [green]{AGENT_DISPLAY_NAME}[/green] "
                f"(name: {AGENT_NAME})"
            )
            console.print("  [dim]Prompt-only agent - MCP tools injected by orchestrator[/dim]")


def list_agents() -> None:
    """List all agents in the AI Foundry project."""
    console.print("[bold blue]Listing Agents[/bold blue]\n")

    client = get_client()

    with client:
        with console.status("Fetching agents..."):
            agents = list(client.agents.list())

        if not agents:
            console.print("[yellow]No agents found[/yellow]")
            return

        table = Table(title=f"Found {len(agents)} Agents")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="green")

        for agent in agents:
            table.add_row(agent.name or "(unnamed)", agent.id)

        console.print(table)


def destroy_agent() -> None:
    """Destroy the agent."""
    console.print(f"[bold red]Destroying {AGENT_DISPLAY_NAME} Agent[/bold red]\n")

    client = get_client()

    with client:
        with console.status("Fetching agents..."):
            agents = list(client.agents.list())

        existing = next((a for a in agents if a.name == AGENT_NAME), None)

        if not existing:
            console.print(f"[yellow]Agent '{AGENT_NAME}' not found[/yellow]")
            return

        console.print(f"Found agent: {existing.name} ({existing.id})")

        if not console.input("\n[bold]Proceed with deletion? [y/N]: [/bold]").lower().startswith("y"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        with console.status(f"Deleting {AGENT_NAME}..."):
            client.agents.delete(agent_name=AGENT_NAME)
            console.print(f"[green]✓[/green] Deleted [red]{AGENT_NAME}[/red]")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        console.print("[bold]Usage:[/bold] python provision_foundry_agent_base.py <command>")
        console.print("\n[bold]Commands:[/bold]")
        console.print("  create   - Create the agent in AI Foundry")
        console.print("  list     - List all agents in the project")
        console.print("  destroy  - Destroy the agent")
        sys.exit(1)

    command = sys.argv[1].lower()

    commands = {
        "create": create_agent,
        "list": list_agents,
        "destroy": destroy_agent,
    }

    if command not in commands:
        console.print(f"[red]Unknown command: {command}[/red]")
        sys.exit(1)

    commands[command]()


if __name__ == "__main__":
    main()
