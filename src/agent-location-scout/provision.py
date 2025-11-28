"""Agent provisioner for Location Scout (Hosted Agent).

Creates and destroys the location-scout hosted agent in Azure AI Foundry Agent Service.
Unlike prompt-based agents, hosted agents require a container image.
"""

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ImageBasedHostedAgentDefinition,
    ProtocolVersionRecord,
    AgentProtocol,
)
from azure.identity import DefaultAzureCredential
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

AGENT_NAME = "location-scout"
AGENT_DISPLAY_NAME = "Location Scout"


def get_client() -> AIProjectClient:
    """Create AI Project client with default credentials."""
    settings = get_settings()
    return AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=settings.azure_ai_foundry_endpoint,
    )


def create_agent() -> None:
    """Create the location-scout hosted agent in AI Foundry.

    This function is idempotent - it will create a new version if agent exists.
    Requires CONTAINER_IMAGE environment variable to be set.
    """
    console.print(f"[bold blue]Creating {AGENT_DISPLAY_NAME} Hosted Agent[/bold blue]\n")

    settings = get_settings()
    
    if not settings.container_image:
        console.print("[red]Error: CONTAINER_IMAGE environment variable not set[/red]")
        console.print("Set it to your GHCR image, e.g.:")
        console.print("  export CONTAINER_IMAGE=ghcr.io/cloud-ai-summit-cz/agent-location-scout:latest")
        sys.exit(1)
    
    console.print(f"Container image: [cyan]{settings.container_image}[/cyan]")
    console.print(f"CPU: {settings.agent_cpu}, Memory: {settings.agent_memory}")
    
    client = get_client()

    with client:
        # Check for existing agent versions
        with console.status("Checking for existing agent..."):
            existing_agents = list(client.agents.list())
            existing = next((a for a in existing_agents if a.name == AGENT_NAME), None)

        if existing:
            console.print(f"[yellow]Found existing agent '{AGENT_NAME}', will create new version[/yellow]")

        # Create hosted agent version
        with console.status(f"Creating {AGENT_DISPLAY_NAME} hosted agent..."):
            try:
                agent_def = ImageBasedHostedAgentDefinition(
                    image=settings.container_image,
                    cpu=settings.agent_cpu,
                    memory=settings.agent_memory,
                    container_protocol_versions=[
                        ProtocolVersionRecord(
                            protocol=AgentProtocol.RESPONSES,
                            version="v1",
                        )
                    ],
                    environment_variables={
                        "AZURE_AI_PROJECT_ENDPOINT": settings.azure_ai_foundry_endpoint,
                        "AZURE_AI_MODEL_DEPLOYMENT_NAME": settings.azure_ai_model_deployment_name,
                    },
                )

                agent = client.agents.create_version(
                    agent_name=AGENT_NAME,
                    definition=agent_def,
                    description=f"{AGENT_DISPLAY_NAME} - LangGraph-based location analysis agent",
                )

                console.print(
                    f"[green]✓[/green] Created [green]{AGENT_DISPLAY_NAME}[/green] "
                    f"(name: {AGENT_NAME}, version: {agent.version})"
                )
                
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to create [red]{AGENT_DISPLAY_NAME}[/red]: {e}")
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
        table.add_column("Type", style="magenta")

        for agent in agents:
            # Try to determine if hosted or prompt-based
            agent_type = "hosted" if hasattr(agent, 'image') else "prompt"
            table.add_row(
                agent.name or "(unnamed)",
                agent.id,
                agent_type,
            )

        console.print(table)


def destroy_agent() -> None:
    """Destroy the location-scout agent (all versions)."""
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
                console.print(f"[green]✓[/green] Deleted [red]{AGENT_NAME}[/red]")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to delete {AGENT_NAME}: {e}")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        console.print("[bold]Usage:[/bold] python provision.py <command>")
        console.print("\n[bold]Commands:[/bold]")
        console.print("  create   - Create/update the hosted agent in AI Foundry")
        console.print("  list     - List all agents in the project")
        console.print("  destroy  - Destroy the agent (all versions)")
        console.print("\n[bold]Required Environment Variables:[/bold]")
        console.print("  AZURE_AI_FOUNDRY_ENDPOINT  - Foundry project endpoint")
        console.print("  CONTAINER_IMAGE            - GHCR image URL (for create)")
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
