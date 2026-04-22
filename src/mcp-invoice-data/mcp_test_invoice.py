"""Test script for Invoice Validation Agent in Azure AI Foundry.

This script sends a test invoice to the agent and prints the validation result.
Uses managed identity for authentication with the new azure-ai-projects SDK (>=2.0.0b1).
"""

import json

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Configuration
PROJECT_ENDPOINT = "https://ai-foundry-mma-ncus.services.ai.azure.com/api/projects/proj-default"
AGENT_NAME = "invoice-validation-agent"

# Test invoice payload
TEST_INVOICE = {
    "invoice_number": "100",
    "invoice_date": "2025-10-15",
    "due_date": None,
    "currency": "EUR",
    "po_number": "PO-534",
    "supplier": {
        "name": "Zava Specialty Coffee",
        "address": "333 3rd Ave, Seattle, WA 12345",
        "email": None,
        "phone": "123-456-7890"
    },
    "bill_to": {
        "name": "Tomas Kubica",
        "address": "Karlinska 1918, Karlin, Czechia",
        "department": "Cofilot Inc"
    },
    "line_items": [
        {
            "description": "Zava Ethiopia for Espresso",
            "quantity": 80,
            "unit_price": 20,
            "uom": "Kg",
            "total": 2000
        }
    ],
    "subtotal": 2000,
    "tax": 300,
    "shipping": 0,
    "total": 2300,
    "confidence": 0.95,
    "notes": ""
}


def main():
    """Run the invoice validation test using the new conversations API."""
    print("🔐 Authenticating with managed identity...")
    
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        # Retrieve the existing agent by name
        print(f"🤖 Getting agent: {AGENT_NAME}")
        agent = project_client.agents.get(agent_name=AGENT_NAME)
        print(f"   Agent retrieved (id: {agent.id}, name: {agent.name}, version: {agent.versions.latest.version})")
        
        # Create a new conversation
        print("📝 Creating conversation...")
        conversation = openai_client.conversations.create()
        print(f"   Conversation ID: {conversation.id}")
        
        # Format the invoice as a message
        message_content = f"""Please validate this invoice:

```json
{json.dumps(TEST_INVOICE, indent=2)}
```

Check if the PO number exists and is valid, and verify the invoice details match the purchase order."""

        # Add the user message to the conversation
        print("💬 Sending invoice for validation...")
        openai_client.conversations.items.create(
            conversation_id=conversation.id,
            items=[{"type": "message", "role": "user", "content": message_content}],
        )
        print("   User message added to conversation")
        
        # Run the agent and get the response
        print("🚀 Running agent...")
        response = openai_client.responses.create(
            conversation=conversation.id,
            extra_body={"agent": {"name": agent.name, "type": "agent_reference"}},
            input="",
        )
        
        print("✅ Agent completed successfully!")
        print("\n" + "=" * 60)
        print("📋 AGENT RESPONSE:")
        print("=" * 60)
        
        # Debug: print full response object
        print(f"Response ID: {response.id}")
        print(f"Response status: {response.status}")
        print(f"Output text: '{response.output_text}'")
        print(f"\nOutput items ({len(response.output)}):")
        for i, item in enumerate(response.output):
            print(f"  [{i}] Type: {item.type}")
            if hasattr(item, 'content'):
                print(f"      Content: {item.content}")
            if hasattr(item, 'name'):
                print(f"      Name: {item.name}")
            if hasattr(item, 'arguments'):
                print(f"      Arguments: {item.arguments}")
            if hasattr(item, 'status'):
                print(f"      Status: {item.status}")
        
        # Get conversation items to see full history
        print("\n" + "-" * 60)
        print("📜 CONVERSATION HISTORY:")
        print("-" * 60)
        conv_items = openai_client.conversations.items.list(conversation_id=conversation.id)
        for item in conv_items:
            print(f"  [{item.type}] {item.role if hasattr(item, 'role') else ''}")
            if hasattr(item, 'content'):
                content = item.content
                if isinstance(content, list):
                    for c in content:
                        if hasattr(c, 'text'):
                            print(f"    Text: {c.text[:200]}..." if len(str(c.text)) > 200 else f"    Text: {c.text}")
                else:
                    print(f"    {str(content)[:500]}")
        
        print("=" * 60)
        
        print("\n✅ Done!")


if __name__ == "__main__":
    main()
