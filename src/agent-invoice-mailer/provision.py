"""Agent provisioner for Invoice Mailer.

Creates and destroys the invoice-mailer-agent in Azure AI Foundry Agent Service.
This agent reviews validation results (especially failed validations) and creates
email drafts summarizing issues and potential resolution steps.
"""

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MCPTool,
    PromptAgentDefinition,
    PromptAgentDefinitionText,
    ResponseTextFormatConfigurationJsonSchema,
)
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

AGENT_NAME = "invoice-mailer-agent"
AGENT_DISPLAY_NAME = "Invoice Mailer Agent"

EMAIL_DRAFT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "email_subject": {
            "type": "string",
            "description": "Email subject including Invoice ID and revocation status",
        },
        "email_to": {
            "type": "string",
            "description": "Recipient email address (supplier email from invoice)",
        },
        "email_cc": {
            "type": "array",
            "items": {"type": "string"},
            "description": "CC recipients (internal stakeholders)",
        },
        "email_body": {
            "type": "string",
            "description": "Email body with issue summary and resolution steps",
        },
        "invoice_id": {
            "type": "string",
            "description": "The invoice number/ID being referenced",
        },
        "po_number": {
            "type": "string",
            "description": "The PO number from the invoice (if available)",
        },
        "validation_status": {
            "type": "string",
            "enum": ["failed", "passed"],
            "description": "Overall validation status",
        },
        "issues_summary": {
            "type": "array",
            "description": "Summary of validation issues",
            "items": {
                "type": "object",
                "properties": {
                    "issue_code": {"type": "string"},
                    "issue_description": {"type": "string"},
                    "suggested_action": {"type": "string"},
                },
                "required": ["issue_code", "issue_description", "suggested_action"],
            },
        },
        "next_steps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of recommended next steps for resolution",
        },
        "urgency": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Urgency level based on issue severity",
        },
        "notes": {
            "type": "string",
            "description": "Additional notes or context",
        },
    },
    "required": [
        "email_subject",
        "email_to",
        "email_body",
        "invoice_id",
        "validation_status",
        "issues_summary",
        "next_steps",
        "urgency",
    ],
}


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
    return template.render()


def create_agent() -> None:
    """Create the invoice-mailer-agent in AI Foundry.

    This function is idempotent - it will delete existing agent before creating new one.
    """
    console.print(f"[bold blue]Creating {AGENT_DISPLAY_NAME}[/bold blue]\n")

    settings = get_settings()
    client = get_client()

    with client:
        # Check for existing agent and delete if found (idempotent)
        with console.status("Checking for existing agent..."):
            existing_agents = list(client.agents.list())
            existing = next((a for a in existing_agents if a.name == AGENT_NAME), None)

        if existing:
            console.print("[yellow]Found existing agent, deleting...[/yellow]")
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

                # Configure MCP tool for invoice data
                mcp_tools = [
                    MCPTool(
                        server_label="MCPInvoiceData",
                        server_url=settings.mcp_invoice_data_url,
                        project_connection_id="MCPInvoiceData",
                        require_approval="never",
                    ),
                ]

                agent_def = PromptAgentDefinition(
                    model=settings.model_deployment_name,
                    instructions=instructions,
                    temperature=0.3,
                    tools=mcp_tools,
                    text=PromptAgentDefinitionText(
                        format=ResponseTextFormatConfigurationJsonSchema(
                            name="EmailDraft",
                            description="Email draft for invoice validation issues",
                            schema=EMAIL_DRAFT_SCHEMA,
                            strict=False,
                        )
                    ),
                )

                client.agents.create(
                    name=AGENT_NAME,
                    definition=agent_def,
                    description=AGENT_DISPLAY_NAME,
                    metadata={
                        "workflow_sequence": "4",
                        "workflow_role": "notification",
                        "workflow_display_name": AGENT_DISPLAY_NAME,
                        "workflow_handoff": "end",
                    },
                )

                console.print(
                    f"[OK] Created [green]{AGENT_DISPLAY_NAME}[/green] "
                    f"(name: {AGENT_NAME})"
                )
                console.print("  Workflow Sequence: 4")
                console.print("  Workflow Role: notification")
                console.print("  Handoff: end")
                console.print("  MCP Tools: MCPInvoiceData")
                console.print("  Output Schema: EmailDraft")

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
    """Destroy the invoice-mailer-agent."""
    console.print(f"[bold red]Destroying {AGENT_DISPLAY_NAME}[/bold red]\n")

    client = get_client()

    with client:
        with console.status("Fetching agents..."):
            agents = list(client.agents.list())

        existing = next((a for a in agents if a.name == AGENT_NAME), None)

        if not existing:
            console.print(f"[yellow]Agent '{AGENT_NAME}' not found[/yellow]")
            return

        console.print(f"Found agent: {existing.name} ({existing.id})")

        if not console.input("\n[bold]Proceed with deletion? [y/N]: [/bold]").lower().startswith(
            "y"
        ):
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
