"""Agent provisioner for Invoice Validation.

Creates and destroys the invoice-validation-agent in Azure AI Foundry Agent Service.
This agent validates invoice data, verifies PO numbers, and applies business rules.

MCP Tools configured at provisioning time:
- mcp-invoice-data: PO validation, vendor lookup, duplicate checks
"""

import argparse
import os
import sys
from typing import Callable

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

AGENT_NAME = "invoice-validation-agent"
AGENT_DISPLAY_NAME = "Invoice Validation Agent"


def _apply_env_overrides(overrides: dict[str, str | None]) -> None:
    """Apply CLI-provided overrides to environment variables.

    Args:
        overrides: Mapping of environment variable names to their desired values.
            Values of None are ignored.

    Notes:
        This clears the cached settings to ensure overrides take effect.
    """
    applied = False
    for key, value in overrides.items():
        if value is None:
            continue
        os.environ[key] = value
        applied = True

    if applied:
        get_settings.cache_clear()


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    The optional flags correspond 1:1 with variables in `.env.example` and are
    applied as environment variables to override local env / `.env` values.
    """
    parser = argparse.ArgumentParser(
        prog="provision.py",
        description="Provision and manage the Invoice Validation agent in Azure AI Foundry.",
    )

    parser.add_argument(
        "--azure-ai-foundry-endpoint",
        dest="azure_ai_foundry_endpoint",
        help="Overrides AZURE_AI_FOUNDRY_ENDPOINT",
    )
    parser.add_argument(
        "--model-deployment-name",
        dest="model_deployment_name",
        help="Overrides MODEL_DEPLOYMENT_NAME",
    )
    parser.add_argument(
        "--mcp-invoice-data-url",
        dest="mcp_invoice_data_url",
        help="Overrides MCP_INVOICE_DATA_URL",
    )
    parser.add_argument(
        "--applicationinsights-connection-string",
        dest="applicationinsights_connection_string",
        help="Overrides APPLICATIONINSIGHTS_CONNECTION_STRING",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create the agent in AI Foundry")
    create.set_defaults(_handler=create_agent)

    list_cmd = subparsers.add_parser("list", help="List all agents in the project")
    list_cmd.set_defaults(_handler=list_agents)

    destroy = subparsers.add_parser("destroy", help="Destroy the agent")
    destroy.set_defaults(_handler=destroy_agent)

    return parser

INVOICE_EXTRACTION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "po_number": {"type": "string"},
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string", "description": "ISO 8601 date"},
        "due_date": {"type": "string", "description": "ISO 8601 date"},
        "currency": {"type": "string", "description": "Three letter ISO currency code"},
        "supplier": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["name"],
        },
        "bill_to": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"type": "string"},
                "department": {"type": "string"},
            },
        },
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "uom": {"type": "string"},
                    "total": {"type": "number"},
                },
                "required": ["description", "quantity", "unit_price", "total"],
            },
        },
        "subtotal": {"type": "number"},
        "tax": {"type": "number"},
        "shipping": {"type": "number"},
        "total": {"type": "number"},
        "confidence": {"type": "number", "description": "0-1 confidence score"},
        "notes": {"type": "string"},
    },
    "required": ["invoice_number", "invoice_date", "supplier", "line_items", "total"],
}

VALIDATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "is_ready_for_posting": {
            "type": "boolean",
            "description": "True only if PO is present AND validated successfully",
        },
        "invoice_validation_status": {
            "type": "string",
            "enum": ["<INV_OK>", "<INV_FAIL>"],
            "description": "<INV_OK> if is_ready_for_posting is true, <INV_FAIL> otherwise",
        },
        "issues": {
            "type": "array",
            "description": "Validation issues found (PO_MISSING or PO_NOT_FOUND)",
            "items": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "enum": ["PO_MISSING", "PO_NOT_FOUND"],
                        "description": "PO_MISSING if no PO provided, PO_NOT_FOUND if PO doesn't exist",
                    },
                    "severity": {"type": "string", "enum": ["error"]},
                    "message": {"type": "string"},
                    "field": {"type": "string", "enum": ["po_number"]},
                },
                "required": ["code", "severity", "message", "field"],
            },
        },
        "normalized_invoice": INVOICE_EXTRACTION_SCHEMA,
        "po_validation_result": {
            "type": "object",
            "description": "Result of PO validation via MCP tool",
            "properties": {
                "po_number": {"type": "string"},
                "is_valid": {"type": "boolean"},
                "tool_name": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["po_number", "is_valid"],
        },
        "business_rules": {
            "type": "array",
            "description": "PO validation rule check",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {
                        "type": "string",
                        "description": "PO must be present and valid",
                    },
                    "passed": {"type": "boolean"},
                    "details": {"type": "string"},
                },
                "required": ["rule", "passed"],
            },
        },
    },
    "required": ["is_ready_for_posting", "invoice_validation_status", "issues", "normalized_invoice", "po_validation_result", "business_rules"],
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
    """Create the invoice-validation-agent in AI Foundry.

    This function is idempotent - it will delete existing agent before creating new one.
    Configures MCP tool for invoice data access.
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
                        require_approval="never",  # Set to "never" for auto-approval
                    ),
                ]

                agent_def = PromptAgentDefinition(
                    model=settings.model_deployment_name,
                    instructions=instructions,
                    temperature=0.1,
                    tools=mcp_tools,
                    text=PromptAgentDefinitionText(
                        format=ResponseTextFormatConfigurationJsonSchema(
                            name="InvoiceValidation",
                            description="Validation results with normalized invoice data",
                            schema=VALIDATION_SCHEMA,
                            strict=False,
                        )
                    ),
                )

                client.agents.create(
                    name=AGENT_NAME,
                    definition=agent_def,
                    description=AGENT_DISPLAY_NAME,
                    metadata={
                        "workflow_sequence": "2",
                        "workflow_role": "validation",
                        "workflow_display_name": AGENT_DISPLAY_NAME,
                        "workflow_handoff": "invoice-process-summary-agent",
                    },
                )

                console.print(
                    f"[OK] Created [green]{AGENT_DISPLAY_NAME}[/green] "
                    f"(name: {AGENT_NAME})"
                )
                console.print("  Workflow Sequence: 2")
                console.print("  Workflow Role: validation")
                console.print("  Handoff: invoice-process-summary-agent")
                console.print("  MCP Tools: MCPInvoiceData")
                console.print("  Output Schema: InvoiceValidation")

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
    """Destroy the invoice-validation-agent."""
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
    parser = _build_parser()
    args = parser.parse_args()

    _apply_env_overrides(
        {
            "AZURE_AI_FOUNDRY_ENDPOINT": args.azure_ai_foundry_endpoint,
            "MODEL_DEPLOYMENT_NAME": args.model_deployment_name,
            "MCP_INVOICE_DATA_URL": args.mcp_invoice_data_url,
            "APPLICATIONINSIGHTS_CONNECTION_STRING": args.applicationinsights_connection_string,
        }
    )

    handler: Callable[[], None] = args._handler
    handler()


if __name__ == "__main__":
    main()
