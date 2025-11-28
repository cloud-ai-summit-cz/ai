#!/usr/bin/env python
"""
Provision script for Location Scout Agent.

Manages Azure AI Foundry hosted agent deployment using SDK and REST API.
Build and push operations are handled by GitHub Actions - this script
only handles remote provisioning via the Azure AI Projects SDK.

Commands:
    deploy           - Create/update hosted agent version in Azure AI Foundry
    start            - Start the hosted agent container
    stop             - Stop the hosted agent container
    restart          - Stop, wait, then start the container
    redeploy         - Full redeployment cycle (stop → delete-container → deploy → start)
    delete-container - Delete the hosted container (keeps agent definition)
    delete           - Delete the hosted agent version
    list             - List all agents in the project
    show             - Show detailed agent information (versions, definition)
    status           - Show current configuration and container status
    invoke           - Test invoke the agent with a simple message

Note: Azure CLI `az cognitiveservices agent` commands are in preview and may
not be available in your CLI version. This script uses REST API directly.
"""

import argparse
import sys
import re
import time

import requests
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ImageBasedHostedAgentDefinition,
    ProtocolVersionRecord,
    AgentProtocol,
)

from config import get_settings


# Data plane API version for container operations
AGENT_API_VERSION = "2025-11-15-preview"


def get_client() -> AIProjectClient:
    """Create and return an AIProjectClient using DefaultAzureCredential."""
    settings = get_settings()
    credential = DefaultAzureCredential()
    return AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=credential,
    )


def get_data_plane_token() -> str:
    """Get an access token for the AI Foundry data plane API."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://ai.azure.com/.default")
    return token.token


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


def get_data_plane_base_url(endpoint: str) -> str:
    """Get the data plane base URL from the Foundry endpoint."""
    account_name, project_name = parse_endpoint(endpoint)
    return f"https://{account_name}.services.ai.azure.com/api/projects/{project_name}"


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

    print(f"\n" + "=" * 60)
    print(f"NEXT STEP - Start the hosted agent:")
    print(f"=" * 60)
    print(f"\n  uv run python provision.py start")
    print(f"\n" + "=" * 60)


def delete_agent() -> None:
    """Delete the hosted agent (latest version)."""
    settings = get_settings()
    client = get_client()

    print(f"Deleting agent: {settings.agent_name}")
    
    # Get the agent to find latest version
    agent = get_agent_by_name(client, settings.agent_name)
    if not agent:
        print(f"Agent '{settings.agent_name}' not found")
        return
    
    version = agent.versions.get("latest", {}).get("version")
    if not version:
        print("No version found for agent")
        return
        
    print(f"Deleting version: {version}")
    client.agents.delete_version(agent_name=settings.agent_name, agent_version=str(version))
    print(f"✓ Agent version {version} deleted")


def get_container_status() -> dict | None:
    """Get the current container status via REST API.
    
    Returns:
        Container status dict or None if not found.
    """
    settings = get_settings()
    base_url = get_data_plane_base_url(settings.azure_ai_foundry_endpoint)
    token = get_data_plane_token()
    
    # Get the latest version number
    client = get_client()
    agent = get_agent_by_name(client, settings.agent_name)
    if not agent:
        return None
    
    version = "1"  # Default version
    if hasattr(agent, 'versions') and agent.versions:
        latest = getattr(agent.versions, 'latest', None)
        if latest:
            version = str(getattr(latest, 'version', '1'))
    
    url = f"{base_url}/agents/{settings.agent_name}/versions/{version}/containers/default"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"api-version": AGENT_API_VERSION}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch container status: {e}")
        return None


def start_agent() -> None:
    """Start the hosted agent container via REST API."""
    settings = get_settings()
    base_url = get_data_plane_base_url(settings.azure_ai_foundry_endpoint)
    token = get_data_plane_token()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get the latest version number
    client = get_client()
    agent = get_agent_by_name(client, settings.agent_name)
    if not agent:
        print(f"Error: Agent '{settings.agent_name}' not found. Deploy it first with: uv run python provision.py deploy")
        sys.exit(1)
    
    version = "1"  # Default version
    if hasattr(agent, 'versions') and agent.versions:
        latest = getattr(agent.versions, 'latest', None)
        if latest:
            version = str(getattr(latest, 'version', '1'))
    
    print(f"Starting hosted agent: {settings.agent_name} (version {version})")
    print(f"  Account: {account_name}")
    print(f"  Project: {project_name}")
    
    url = f"{base_url}/agents/{settings.agent_name}/versions/{version}/containers/default:start"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": AGENT_API_VERSION}
    
    response = requests.post(url, headers=headers, params=params, json={}, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    print(f"✓ Start command sent successfully")
    print(f"  Operation ID: {result.get('id', 'N/A')}")
    print(f"  Status: {result.get('status', 'N/A')}")
    
    container = result.get('container', {})
    print(f"  Container Status: {container.get('status', 'N/A')}")
    
    # Poll for status
    print(f"\nWaiting for container to start...")
    for i in range(30):  # Wait up to 5 minutes
        time.sleep(10)
        status = get_container_status()
        if status:
            container_status = status.get('status', 'Unknown')
            error_msg = status.get('error_message', '')
            print(f"  [{i+1}] Container status: {container_status}")
            
            if error_msg:
                print(f"  Error: {error_msg}")
                break
                
            if container_status == "Running":
                print(f"\n✓ Container is now running!")
                return
            elif container_status in ["Failed", "Stopped"]:
                print(f"\n✗ Container failed to start: {container_status}")
                if error_msg:
                    print(f"  Error: {error_msg}")
                sys.exit(1)
    
    print(f"\n⚠ Container is still starting. Check status with: uv run python provision.py status")


def stop_agent() -> None:
    """Stop the hosted agent container via REST API."""
    settings = get_settings()
    base_url = get_data_plane_base_url(settings.azure_ai_foundry_endpoint)
    token = get_data_plane_token()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get the latest version number
    client = get_client()
    agent = get_agent_by_name(client, settings.agent_name)
    if not agent:
        print(f"Error: Agent '{settings.agent_name}' not found.")
        sys.exit(1)
    
    version = "1"  # Default version
    if hasattr(agent, 'versions') and agent.versions:
        latest = getattr(agent.versions, 'latest', None)
        if latest:
            version = str(getattr(latest, 'version', '1'))
    
    print(f"Stopping hosted agent: {settings.agent_name} (version {version})")
    print(f"  Account: {account_name}")
    print(f"  Project: {project_name}")
    
    url = f"{base_url}/agents/{settings.agent_name}/versions/{version}/containers/default:stop"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": AGENT_API_VERSION}
    
    response = requests.post(url, headers=headers, params=params, json={}, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    print(f"✓ Stop command sent successfully")
    print(f"  Operation ID: {result.get('id', 'N/A')}")
    print(f"  Status: {result.get('status', 'N/A')}")


def delete_container() -> None:
    """Delete the hosted agent container via REST API."""
    settings = get_settings()
    base_url = get_data_plane_base_url(settings.azure_ai_foundry_endpoint)
    token = get_data_plane_token()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get the latest version number
    client = get_client()
    agent = get_agent_by_name(client, settings.agent_name)
    if not agent:
        print(f"Error: Agent '{settings.agent_name}' not found.")
        sys.exit(1)
    
    version = agent.versions.get("latest", {}).get("version", "1")
    
    print(f"Deleting hosted container: {settings.agent_name} (version {version})")
    print(f"  Account: {account_name}")
    print(f"  Project: {project_name}")
    
    url = f"{base_url}/agents/{settings.agent_name}/versions/{version}/containers/default:delete"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": AGENT_API_VERSION}
    
    response = requests.post(url, headers=headers, params=params, json={}, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    print(f"✓ Delete container command sent successfully")
    print(f"  Operation ID: {result.get('id', 'N/A')}")
    print(f"  Status: {result.get('status', 'N/A')}")


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
    """Show current configuration and container status."""
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
            version = "1"
            if hasattr(agent, 'versions') and agent.versions:
                latest = getattr(agent.versions, 'latest', None)
                if latest:
                    version = str(getattr(latest, 'version', '1'))
                    print(f"Latest Version: {version}")
            
            # Get container status
            container = get_container_status()
            if container:
                print(f"\nContainer Status:")
                print(f"  Status:       {container.get('status', 'Unknown')}")
                print(f"  Min Replicas: {container.get('min_replicas', 'N/A')}")
                print(f"  Max Replicas: {container.get('max_replicas', 'N/A')}")
                print(f"  Created:      {container.get('created_at', 'N/A')}")
                print(f"  Updated:      {container.get('updated_at', 'N/A')}")
                error_msg = container.get('error_message', '')
                if error_msg:
                    print(f"  Error:        {error_msg}")
            else:
                print(f"\nContainer Status: Not deployed")
                print(f"  Run 'uv run python provision.py start' to start the container")
        else:
            print(f"\nAgent Status: Not deployed")
            print(f"  Run 'uv run python provision.py deploy' to deploy")
    except Exception as e:
        print(f"\nCould not fetch agent status: {e}")


def show_agent() -> None:
    """Show detailed agent information including all versions."""
    settings = get_settings()
    base_url = get_data_plane_base_url(settings.azure_ai_foundry_endpoint)
    token = get_data_plane_token()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    print(f"Agent Details: {settings.agent_name}")
    print("=" * 60)
    
    # Get agent info via REST API for more details
    url = f"{base_url}/agents/{settings.agent_name}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"api-version": AGENT_API_VERSION}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 404:
            print(f"Agent '{settings.agent_name}' not found.")
            return
        response.raise_for_status()
        agent_data = response.json()
        
        print(f"ID: {agent_data.get('id', 'N/A')}")
        print(f"Name: {agent_data.get('name', 'N/A')}")
        
        # Show versions
        versions = agent_data.get('versions', {})
        print(f"\nVersions:")
        for version_key, version_data in versions.items():
            print(f"\n  [{version_key}]")
            print(f"    Version: {version_data.get('version', 'N/A')}")
            print(f"    Description: {version_data.get('description', 'N/A')}")
            print(f"    Created: {version_data.get('created_at', 'N/A')}")
            
            definition = version_data.get('definition', {})
            kind = definition.get('kind', 'N/A')
            print(f"    Kind: {kind}")
            
            if kind == 'hosted':
                print(f"    Image: {definition.get('image', 'N/A')}")
                print(f"    CPU: {definition.get('cpu', 'N/A')}")
                print(f"    Memory: {definition.get('memory', 'N/A')}")
                protocols = definition.get('container_protocol_versions', [])
                if protocols:
                    for p in protocols:
                        print(f"    Protocol: {p.get('protocol', 'N/A')} {p.get('version', '')}")
                env_vars = definition.get('environment_variables', {})
                if env_vars:
                    print(f"    Environment Variables:")
                    for k, v in env_vars.items():
                        # Mask sensitive values
                        if 'key' in k.lower() or 'secret' in k.lower():
                            v = '***'
                        print(f"      {k}: {v}")
            elif kind == 'prompt':
                print(f"    Model: {definition.get('model', 'N/A')}")
                instructions = definition.get('instructions', '')
                if instructions:
                    preview = instructions[:100] + '...' if len(instructions) > 100 else instructions
                    print(f"    Instructions: {preview}")
        
        # Get container status for hosted agents
        container = get_container_status()
        if container:
            print(f"\nContainer:")
            print(f"  Status: {container.get('status', 'Unknown')}")
            print(f"  Replicas: {container.get('min_replicas', 'N/A')}-{container.get('max_replicas', 'N/A')}")
            error_msg = container.get('error_message', '')
            if error_msg:
                print(f"  Error: {error_msg}")
                
    except requests.exceptions.RequestException as e:
        print(f"Error fetching agent details: {e}")


def restart_agent() -> None:
    """Restart the hosted agent container (stop + start)."""
    settings = get_settings()
    print(f"Restarting agent: {settings.agent_name}")
    print("-" * 40)
    
    # Stop
    print("\n[1/3] Stopping container...")
    try:
        stop_agent()
    except Exception as e:
        print(f"  Warning: Stop failed (may already be stopped): {e}")
    
    # Wait for stop
    print("\n[2/3] Waiting for container to stop...")
    for i in range(12):  # Wait up to 2 minutes
        time.sleep(10)
        status = get_container_status()
        if status:
            container_status = status.get('status', 'Unknown')
            print(f"  [{i+1}] Status: {container_status}")
            if container_status == "Stopped":
                break
        else:
            print(f"  [{i+1}] Container not found")
            break
    
    # Start
    print("\n[3/3] Starting container...")
    start_agent()
    print("\n✓ Restart complete!")


def redeploy_agent() -> None:
    """Full redeployment cycle: stop → delete-container → deploy → start.
    
    Use this when you've pushed a new container image and need to update
    the running agent to use the new image.
    """
    settings = get_settings()
    print(f"Redeploying agent: {settings.agent_name}")
    print("=" * 50)
    print("This will:")
    print("  1. Stop the running container")
    print("  2. Delete the container deployment")
    print("  3. Create a new agent version")
    print("  4. Start the new container")
    print("=" * 50)
    
    # Check current state
    container = get_container_status()
    
    # Step 1: Stop if running
    if container and container.get('status') == 'Running':
        print("\n[1/4] Stopping container...")
        try:
            stop_agent()
            # Wait for stop
            for i in range(12):
                time.sleep(10)
                status = get_container_status()
                if status and status.get('status') == 'Stopped':
                    print("  Container stopped.")
                    break
                print(f"  Waiting... ({i+1})")
        except Exception as e:
            print(f"  Warning: {e}")
    else:
        print("\n[1/4] Container not running, skipping stop.")
    
    # Step 2: Delete container
    print("\n[2/4] Deleting container deployment...")
    try:
        delete_container()
        time.sleep(5)  # Brief wait
    except Exception as e:
        print(f"  Warning: {e}")
    
    # Step 3: Deploy new version
    print("\n[3/4] Deploying new agent version...")
    deploy_foundry()
    
    # Step 4: Start
    print("\n[4/4] Starting container...")
    start_agent()
    
    print("\n" + "=" * 50)
    print("✓ Redeployment complete!")
    print("=" * 50)


def invoke_agent() -> None:
    """Test invoke the agent with a simple message."""
    settings = get_settings()
    
    print(f"Invoking agent: {settings.agent_name}")
    print("-" * 40)
    
    # Check container status first
    container = get_container_status()
    if not container or container.get('status') != 'Running':
        print("Error: Container is not running.")
        print("Start it with: uv run python provision.py start")
        sys.exit(1)
    
    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import AgentReference
        from azure.identity import DefaultAzureCredential
        
        client = AIProjectClient(
            endpoint=settings.azure_ai_foundry_endpoint,
            credential=DefaultAzureCredential()
        )
        
        # Get latest version
        agent = get_agent_by_name(client, settings.agent_name)
        version = "1"
        if agent and hasattr(agent, 'versions') and agent.versions:
            latest = getattr(agent.versions, 'latest', None)
            if latest:
                version = str(getattr(latest, 'version', '1'))
        
        print(f"  Version: {version}")
        print(f"  Sending test message...")
        
        # Use the AIProjectClient's built-in OpenAI client
        # It handles auth and API version automatically
        openai_client = client.get_openai_client()
        
        agent_ref = AgentReference(name=settings.agent_name, version=version)
        
        response = openai_client.responses.create(
            input=[{"role": "user", "content": "Hello! What can you help me with?"}],
            extra_body={"agent": agent_ref.as_dict()}
        )
        
        print(f"\n  Response Status: {response.status}")
        
        if response.error:
            print(f"  Error Code: {response.error.code}")
            print(f"  Error Message: {response.error.message}")
        elif hasattr(response, 'output_text') and response.output_text:
            print(f"\n  Agent Response:")
            print(f"  {response.output_text}")
        elif response.output:
            print(f"\n  Output: {response.output}")
        else:
            print(f"\n  (No output text returned)")
            
    except ImportError as e:
        print(f"Error: Missing required package: {e}")
        print("Install with: uv add azure-ai-projects")
        sys.exit(1)
    except Exception as e:
        print(f"Error invoking agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Location Scout Agent provisioning via Azure AI Foundry SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  deploy           Create/update hosted agent version (idempotent)
  start            Start the hosted agent container
  stop             Stop the hosted agent container
  restart          Stop and start the container (picks up RBAC changes)
  redeploy         Full cycle: stop → delete-container → deploy → start
  delete-container Delete the hosted container (keeps agent version)
  delete           Delete the hosted agent version
  list             List all agents in the project
  show             Show detailed agent info (versions, definition, env vars)
  status           Show current configuration and container status
  invoke           Test invoke the agent with a simple message

Typical workflow (first deployment):
  1. uv run python provision.py deploy   # Create agent version
  2. uv run python provision.py start    # Start the container
  3. uv run python provision.py status   # Check status
  4. uv run python provision.py invoke   # Test the agent

Update workflow (new container image):
  uv run python provision.py redeploy    # Full redeployment cycle
  
  Or step by step:
  1. uv run python provision.py stop
  2. uv run python provision.py delete-container
  3. uv run python provision.py deploy
  4. uv run python provision.py start

To remove an agent completely:
  1. uv run python provision.py stop
  2. uv run python provision.py delete-container
  3. uv run python provision.py delete

Note: Container logs are sent to Application Insights via OpenTelemetry.
View them in the Foundry portal under Monitoring → Traces.
        """,
    )
    parser.add_argument(
        "command",
        choices=[
            "deploy", "start", "stop", "restart", "redeploy",
            "delete-container", "delete", "list", "show", "status", "invoke"
        ],
        help="Command to execute",
    )

    args = parser.parse_args()

    commands = {
        "deploy": deploy_foundry,
        "start": start_agent,
        "stop": stop_agent,
        "restart": restart_agent,
        "redeploy": redeploy_agent,
        "delete-container": delete_container,
        "delete": delete_agent,
        "list": list_agents,
        "show": show_agent,
        "status": show_status,
        "invoke": invoke_agent,
    }

    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
