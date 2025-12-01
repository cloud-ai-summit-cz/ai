"""Agent provisioner for Synthesizer.

Creates and destroys the synthesizer agent in Azure AI Foundry Agent Service.

NOTE: MCP Scratchpad is NOT configured at agent creation time.
The orchestrator provides session-scoped MCP tools dynamically at runtime
with proper X-Session-ID headers for session isolation.
See: agent-research-orchestrator/orchestrator.py::_get_session_mcp_tool()
"""

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from jinja2 import Template
from rich.console import Console
from rich.table import Table

from config import get_settings

# Force UTF-8 output for subprocess compatibility
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore
os.environ["PYTHONIOENCODING"] = "utf-8"

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
    """Load and render the system prompt template."""
    settings = get_settings()
    template_content = settings.get_prompt("system_prompt")
    template = Template(template_content)
    return template.render(company_name="Cofilot")


def create_agent() -> None:
    """Create the synthesizer agent in AI Foundry.

    This function is idempotent - it will delete existing agent before creating new one.
    
    NOTE: MCP Scratchpad tools are provided by the orchestrator at runtime,
    not configured here. This ensures session isolation via X-Session-ID headers.
    """
    console.print(f"[bold blue]Creating {AGENT_DISPLAY_NAME} Agent[/bold blue]\n")

    settings = get_settings()
    client = get_client()

    with client:
        # Check for existing agent and delete if found (idempotent)
        with console.status("Checking for existing agent..."):
            existing_agents = list(client.agents.list())
            existing = next((a for a in existing_agents if a.name == AGENT_NAME), None)

        if existing:
            console.print(f"[yellow]Found existing agent, deleting...[/yellow]")
            with console.status(f"Deleting existing {AGENT_NAME}..."):
                try:
                    client.agents.delete(agent_name=AGENT_NAME)
                    console.print(f"[OK] Deleted existing [dim]{AGENT_NAME}[/dim]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not delete {AGENT_NAME}: {e}[/yellow]")

        # Create agent
        with console.status(f"Creating {AGENT_DISPLAY_NAME}..."):
            try:
                instructions = get_instructions()

                # NOTE: No tools configured here - MCP Scratchpad is injected
                # by the orchestrator at runtime with session-scoped headers
                agent_def = PromptAgentDefinition(
                    model=settings.model_deployment_name,
                    instructions=instructions,
                )

                agent = client.agents.create(
                    name=AGENT_NAME,
                    definition=agent_def,
                    description=AGENT_DISPLAY_NAME,
                )

                console.print(
                    f"[OK] Created [green]{AGENT_DISPLAY_NAME}[/green] "
                    f"(name: {AGENT_NAME})"
                )
                
            except Exception as e:
                console.print(f"[FAIL] Failed to create [red]{AGENT_DISPLAY_NAME}[/red]: {e}")
                raise


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
            table.add_row(
                agent.name or "(unnamed)",
                agent.id,
            )

        console.print(table)


def destroy_agent() -> None:
    """Destroy the synthesizer agent."""
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
            try:
                client.agents.delete(agent_name=AGENT_NAME)
                console.print(f"[OK] Deleted [red]{AGENT_NAME}[/red]")
            except Exception as e:
                console.print(f"[FAIL] Failed to delete {AGENT_NAME}: {e}")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        console.print("[bold]Usage:[/bold] python provision.py <command>")
        console.print("\n[bold]Commands:[/bold]")
        console.print("  create   - Create the agent in AI Foundry")
        console.print("  list     - List all agents in the project")
        console.print("  destroy  - Destroy the agent")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "create":
        create_agent()
    elif command == "list":
        list_agents()
    elif command == "destroy":
        destroy_agent()
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
