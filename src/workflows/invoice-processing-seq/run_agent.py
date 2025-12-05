"""Simple runner for invoice-intake-agent.

Demonstrates how to retrieve and run an existing agent using the Azure AI Projects SDK.
This follows the sample pattern from:
https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-projects/samples/agents/sample_agent_retrieve_basic.py
"""

import base64
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Configuration
ENDPOINT = "https://ai-foundry-mma-ncus.services.ai.azure.com/api/projects/proj-default"
AGENT_NAME = "invoice-intake-agent"


def run_invoice_intake(invoice_path: Path | None = None) -> str:
    """Run the invoice-intake-agent on an invoice image.

    Args:
        invoice_path: Path to the invoice image. Defaults to data/invoice1.jpg.

    Returns:
        The agent's response text (JSON extraction result).
    """
    if invoice_path is None:
        invoice_path = Path(__file__).resolve().parent / "data" / "invoice1.jpg"

    # Load invoice image as base64
    with invoice_path.open("rb") as f:
        base64_invoice = base64.b64encode(f.read()).decode("ascii")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=ENDPOINT, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        # Retrieve the existing agent
        agent = project_client.agents.get(agent_name=AGENT_NAME)
        print(f"Agent retrieved (id: {agent.id}, name: {agent.name})")

        # Create a new conversation
        conversation = openai_client.conversations.create()
        print(f"Created conversation (id: {conversation.id})")

        # Add user message with the invoice image
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Please extract the data from this invoice."},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_invoice}"},
                    ],
                }
            ],
        )
        print("Added invoice image to conversation")

        # Run the agent
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
            input="",
        )

        print(f"Response completed")
        print(f"Output:\n{response.output_text}")

        return response.output_text


def main() -> None:
    """CLI entry point."""
    import sys

    invoice_path = None
    if len(sys.argv) > 1:
        invoice_path = Path(sys.argv[1])
        if not invoice_path.exists():
            print(f"Error: Invoice file not found: {invoice_path}")
            sys.exit(1)

    result = run_invoice_intake(invoice_path)
    print("\n--- Extracted Invoice Data ---")
    print(result)


if __name__ == "__main__":
    main()
