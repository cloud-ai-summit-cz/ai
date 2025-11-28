#!/usr/bin/env python
"""
Provision script for Location Scout Agent.

Manages Azure AI Foundry hosted agent deployment using SDK v2.
Build and push operations are handled by GitHub Actions - this script
only handles remote provisioning via the Azure AI Projects SDK.

Commands:
    deploy  - Create/update hosted agent version in Azure AI Foundry (idempotent)
    delete  - Delete the hosted agent
    list    - List all agents
    status  - Show current configuration

Note: Starting hosted agents requires the Azure Portal or Azure CLI.
The CLI command `az cognitiveservices agent start` is available in preview.
"""

import argparse
import sys
import re

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ImageBasedHostedAgentDefinition,
    ProtocolVersionRecord,
    AgentProtocol,
)

from config import get_settings


def get_client() -> AIProjectClient:
    """Create and return an AIProjectClient using DefaultAzureCredential."""
    settings = get_settings()
    credential = DefaultAzureCredential()
    return AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=credential,
    )


def parse_endpoint(endpoint: str) -> tuple[str, str]:
    """Parse the Foundry endpoint to extract account and project names.
    
    Endpoint format: https://<account>.services.ai.azure.com/api/projects/<project>
    
    Returns:
        Tuple of (account_name, project_name)
    """
    match = re.match(
        r"https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)",
        endpoint
    )
    if match:
        return match.group(1), match.group(2)
    
    raise ValueError(f"Cannot parse endpoint: {endpoint}")


def get_agent_by_name(client: AIProjectClient, agent_name: str):
    """Find an agent by name. Returns None if not found."""
    for agent in client.agents.list():
        if agent.name == agent_name:
            return agent
    return None


def deploy_foundry() -> None:
    """Deploy the agent to Azure AI Foundry as a hosted container agent.
    
    Idempotent: creates new version if agent exists, or creates new agent.
    """
    settings = get_settings()
    client = get_client()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)

    print(f"Deploying hosted agent: {settings.agent_name}")
    print(f"  Container image: {settings.container_image}")
    print(f"  CPU: {settings.agent_cpu}, Memory: {settings.agent_memory}")
    print(f"  Account: {account_name}, Project: {project_name}")

    # Check if agent already exists
    existing = get_agent_by_name(client, settings.agent_name)
    if existing:
        print(f"  Agent already exists")
        print("  Creating new version...")

    definition = ImageBasedHostedAgentDefinition(
        container_protocol_versions=[
            ProtocolVersionRecord(protocol=AgentProtocol.RESPONSES, version="v1")
        ],
        cpu=settings.agent_cpu,
        memory=settings.agent_memory,
        image=settings.container_image,
        environment_variables={
            "AZURE_AI_PROJECT_ENDPOINT": settings.azure_ai_foundry_endpoint,
            "MODEL_NAME": settings.azure_openai_deployment,
        },
    )

    result = client.agents.create_version(
        agent_name=settings.agent_name,
        definition=definition,
    )
    print(f"✓ Agent version created successfully")
    print(f"  Agent ID: {result.id}")
    print(f"  Agent Name: {result.name}")
    print(f"  Version: {result.version}")

    # Provide instructions for starting the agent
    print(f"\n" + "=" * 60)
    print(f"NEXT STEPS - Start the hosted agent:")
    print(f"=" * 60)
    print(f"\nOption 1: Azure AI Foundry Portal")
    print(f"  1. Go to https://ai.azure.com")
    print(f"  2. Navigate to your project: {project_name}")
    print(f"  3. Go to Agents > {settings.agent_name}")
    print(f"  4. Click 'Start hosted agent' button")
    print(f"\nOption 2: Azure CLI (when available)")
    print(f"  az cognitiveservices agent start \\")
    print(f"    --account-name {account_name} \\")
    print(f"    --project-name {project_name} \\")
    print(f"    --name {settings.agent_name} \\")
    print(f"    --agent-version {result.version}")
    print(f"\n" + "=" * 60)


def delete_agent() -> None:
    """Delete the hosted agent."""
    settings = get_settings()
    client = get_client()

    print(f"Deleting agent: {settings.agent_name}")
    client.agents.delete_version(name=settings.agent_name)
    print(f"✓ Agent deleted")


def list_agents() -> None:
    """List all agents in the project."""
    client = get_client()
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)

    print(f"Listing agents in project: {project_name}")
    print("-" * 50)
    
    agents = list(client.agents.list())
    
    if not agents:
        print("No agents found.")
        return

    for agent in agents:
        name = getattr(agent, 'name', 'unknown')
        kind = "hosted" if hasattr(agent, 'versions') else getattr(agent, 'kind', 'unknown')
        print(f"  - {name}")
        print(f"    Kind: {kind}")
        
        # Try to get version info
        if hasattr(agent, 'versions') and agent.versions:
            latest = getattr(agent.versions, 'latest', None)
            if latest:
                print(f"    Latest version: {getattr(latest, 'version', 'unknown')}")


def show_status() -> None:
    """Show current configuration and status."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    print("Location Scout Agent - Configuration")
    print("=" * 50)
    print(f"Agent Name:       {settings.agent_name}")
    print(f"Container Image:  {settings.container_image}")
    print(f"Model:            {settings.azure_openai_deployment}")
    print(f"CPU:              {settings.agent_cpu}")
    print(f"Memory:           {settings.agent_memory}")
    print("-" * 50)
    print(f"Foundry Account:  {account_name}")
    print(f"Foundry Project:  {project_name}")
    print(f"Foundry Endpoint: {settings.azure_ai_foundry_endpoint}")
    print("=" * 50)
    
    # Try to get agent status
    try:
        client = get_client()
        agent = get_agent_by_name(client, settings.agent_name)
        if agent:
            print(f"\nAgent Status: Registered")
            if hasattr(agent, 'versions') and agent.versions:
                latest = getattr(agent.versions, 'latest', None)
                if latest:
                    print(f"Latest Version: {getattr(latest, 'version', 'unknown')}")
        else:
            print(f"\nAgent Status: Not deployed")
    except Exception as e:
        print(f"\nCould not fetch agent status: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Location Scout Agent provisioning via Azure AI Foundry SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  deploy   Create/update hosted agent version (idempotent)
  delete   Delete the hosted agent
  list     List all agents in the project
  status   Show current configuration

Note: Starting hosted agents requires Azure Portal or CLI.
Build and push operations are handled by GitHub Actions.
        """,
    )
    parser.add_argument(
        "command",
        choices=["deploy", "delete", "list", "status"],
        help="Command to execute",
    )

    args = parser.parse_args()

    commands = {
        "deploy": deploy_foundry,
        "delete": delete_agent,
        "list": list_agents,
        "status": show_status,
    }

    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
