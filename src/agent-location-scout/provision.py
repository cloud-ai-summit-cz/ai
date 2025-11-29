#!/usr/bin/env python
"""
Provision script for Location Scout Agent.

Manages Azure AI Foundry hosted agent deployment using Azure CLI commands.
Container operations (start, stop, delete) use `az cognitiveservices agent` CLI (preview).
Agent creation uses the Python SDK since it supports ImageBasedHostedAgentDefinition.

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

Requires:
    - Azure CLI 2.80.0+ with `az cognitiveservices agent` preview commands
    - azure-ai-projects Python SDK for agent creation
"""

import argparse
import json
import re
import subprocess
import sys
import time
from typing import Any

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables from .env file
load_dotenv()

from azure.ai.projects.models import (
    ImageBasedHostedAgentDefinition,
    ProtocolVersionRecord,
    AgentProtocol,
)

from config import get_settings


def run_az_command(args: list[str], check: bool = True) -> dict[str, Any] | list[Any] | None:
    """Run an Azure CLI command and return parsed JSON output.
    
    Args:
        args: List of command arguments (without 'az' prefix)
        check: If True, raise exception on non-zero exit code
        
    Returns:
        Parsed JSON output, or None if command failed and check=False
    """
    cmd = ["az"] + args + ["--output", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            shell=True,  # Required on Windows to find 'az' command
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running: az {' '.join(args)}")
            print(f"  Exit code: {e.returncode}")
            if e.stderr:
                print(f"  Error: {e.stderr}")
            raise
        return None
    except json.JSONDecodeError:
        # Some commands return non-JSON output
        return None


def get_client() -> AIProjectClient:
    """Create and return an AIProjectClient using DefaultAzureCredential."""
    settings = get_settings()
    # Use DefaultAzureCredential which supports Azure CLI, VS Code, etc.
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


def get_agent_versions_cli(agent_name: str) -> list[dict] | None:
    """Get all versions of an agent using Azure CLI."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    return run_az_command([
        "cognitiveservices", "agent", "list-versions",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", agent_name,
    ], check=False)


def get_latest_version(client: Any, agent_name: str) -> str:
    """Get the latest version number for an agent using Azure CLI.
    
    Args:
        client: Ignored (kept for compatibility)
        agent_name: Name of the agent
        
    Returns:
        Latest version string, or '1' if not found.
    """
    versions = get_agent_versions_cli(agent_name)
    if not versions:
        return "1"
        
    # Sort by version number (assuming integer versions)
    try:
        sorted_versions = sorted(
            versions, 
            key=lambda v: int(v.get('version', '0')), 
            reverse=True
        )
        if sorted_versions:
            return sorted_versions[0].get('version', '1')
    except ValueError:
        # Fallback for non-integer versions
        pass
        
    return "1"


def deploy_foundry() -> None:
    """Deploy the agent to Azure AI Foundry as a hosted container agent.
    
    Uses Python SDK for agent creation since it supports ImageBasedHostedAgentDefinition.
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
    # Use CLI to check existence to avoid SDK credential issues
    existing_versions = get_agent_versions_cli(settings.agent_name)
    if existing_versions:
        print(f"  Agent already exists")
        print("  Creating new version...")

    # Extract the Azure OpenAI endpoint from the Foundry account name
    # Foundry project endpoint: https://<account>.services.ai.azure.com/api/projects/<project>
    # Azure OpenAI endpoint:    https://<account>.cognitiveservices.azure.com/
    # 
    # CRITICAL: LangChain/OpenAI SDK requires the cognitiveservices.azure.com endpoint,
    # NOT the services.ai.azure.com endpoint! The latter is for Foundry project APIs.
    account_name, _ = parse_endpoint(settings.azure_ai_foundry_endpoint)
    azure_openai_endpoint = f"https://{account_name}.cognitiveservices.azure.com"
    
    # Environment variables for langchain-openai (init_chat_model)
    # The adapter/langchain auto-configure from these standard env vars
    env_vars = {
        # Azure OpenAI endpoint - the base AI Services endpoint (NOT the project endpoint)
        # From MS docs: https://ai-foundry-<resource>.services.ai.azure.com/
        "AZURE_OPENAI_ENDPOINT": azure_openai_endpoint,
        # Model deployment name (e.g., "gpt-4o", "gpt-5")
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": settings.azure_openai_deployment,
        # API version for Azure OpenAI
        "OPENAI_API_VERSION": "2024-10-21",
    }
    
    # Add Application Insights connection string if available
    import os
    app_insights = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if app_insights:
        print("  Configuring Application Insights...")
        env_vars["APPLICATIONINSIGHTS_CONNECTION_STRING"] = app_insights
    else:
        print("  Warning: APPLICATIONINSIGHTS_CONNECTION_STRING not set. Logs will not be collected.")
    
    # Add tenant ID if set (helps with auth in multi-tenant scenarios)
    tenant_id = os.getenv("AZURE_TENANT_ID")
    if tenant_id:
        env_vars["AZURE_TENANT_ID"] = tenant_id

    definition = ImageBasedHostedAgentDefinition(
        container_protocol_versions=[
            ProtocolVersionRecord(protocol=AgentProtocol.RESPONSES, version="v1")
        ],
        cpu=settings.agent_cpu,
        memory=settings.agent_memory,
        image=settings.container_image,
        environment_variables=env_vars,
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
    """Delete the hosted agent (latest version) using Python SDK."""
    settings = get_settings()
    client = get_client()

    print(f"Deleting agent: {settings.agent_name}")
    
    version = get_latest_version(None, settings.agent_name)
    if not version:
        print("No version found for agent")
        return
        
    print(f"Deleting version: {version}")
    client.agents.delete_version(agent_name=settings.agent_name, agent_version=str(version))
    print(f"✓ Agent version {version} deleted")

def get_container_status_cli() -> dict | None:
    """Get container status by calling start command (it returns current status).
    
    Note: Azure CLI doesn't have a direct container status command,
    but the start command returns container status even if already running.
    """
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    # Client not needed for version lookup anymore
    version = get_latest_version(None, settings.agent_name)
    
    # Use start command to get current container status (it's idempotent)
    # Use start command to get current container status (it's idempotent)
    result = run_az_command([
        "cognitiveservices", "agent", "start",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ], check=False)
    
    if result and 'container' in result:
        return result['container']
    return None


def start_agent() -> None:
    """Start the hosted agent container using Azure CLI."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get latest version
    version = get_latest_version(None, settings.agent_name)
    
    print(f"Starting hosted agent: {settings.agent_name} (version {version})")
    print(f"  Account: {account_name}")
    print(f"  Project: {project_name}")
    
    result = run_az_command([
        "cognitiveservices", "agent", "start",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ])
    
    if result:
        print(f"✓ Start command sent successfully")
        print(f"  Operation ID: {result.get('id', 'N/A')}")
        print(f"  Status: {result.get('status', 'N/A')}")
        
        container = result.get('container', {})
        print(f"  Container Status: {container.get('status', 'N/A')}")
    
    # Poll for status
    print(f"\nWaiting for container to start...")
    for i in range(30):  # Wait up to 5 minutes
        time.sleep(10)
        status = get_container_status_cli()
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
    """Stop the hosted agent container using Azure CLI."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get latest version
    version = get_latest_version(None, settings.agent_name)
    
    print(f"Stopping hosted agent: {settings.agent_name} (version {version})")
    print(f"  Project: {project_name}")
    
    result = run_az_command([
        "cognitiveservices", "agent", "stop",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ])
    
    if result:
        print(f"✓ Stop command sent successfully")
        print(f"  Operation ID: {result.get('id', 'N/A')}")
        print(f"  Status: {result.get('status', 'N/A')}")


def delete_container() -> None:
    """Delete the hosted agent container using Azure CLI."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    # Get latest version
    version = get_latest_version(None, settings.agent_name)
    
    print(f"Deleting hosted container: {settings.agent_name} (version {version})")
    
    result = run_az_command([
        "cognitiveservices", "agent", "delete-deployment",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ])
    
    if result:
        print(f"✓ Delete container command sent successfully")
        print(f"  Operation ID: {result.get('id', 'N/A')}")
        print(f"  Status: {result.get('status', 'N/A')}")


def list_agents() -> None:
    """List all agents in the project using Azure CLI."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)

    print(f"Listing agents in project: {project_name}")
    print("-" * 50)
    
    result = run_az_command([
        "cognitiveservices", "agent", "list",
        "--account-name", account_name,
        "--project-name", project_name,
    ])
    
    if not result:
        print("No agents found.")
        return
    
    for agent in result:
        name = agent.get('name', 'unknown')
        versions = agent.get('versions', {})
        latest = versions.get('latest', {})
        definition = latest.get('definition', {})
        kind = definition.get('kind', 'prompt')
        version = latest.get('version', 'N/A')
        
        print(f"  - {name}")
        print(f"    Kind: {kind}")
        print(f"    Latest version: {version}")
        
        if kind == 'hosted':
            print(f"    Image: {definition.get('image', 'N/A')}")


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
        versions = get_agent_versions_cli(settings.agent_name)
        if versions:
            print(f"\nAgent Status: Registered")
            version = get_latest_version(None, settings.agent_name)
            print(f"Latest Version: {version}")
            
            # Get container status
            container = get_container_status_cli()
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
    print(f"Agent Details: {settings.agent_name}")
    print("=" * 60)
    
    result = run_az_command([
        "cognitiveservices", "agent", "show",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
    ], check=False)
    
    if not result:
        print(f"Agent '{settings.agent_name}' not found.")
        return
    
    print(f"ID: {result.get('id', 'N/A')}")
    print(f"Name: {result.get('name', 'N/A')}")
    
    # Show versions
    versions = result.get('versions', {})
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
    
    # Get container status
    container = get_container_status_cli()
    if container:
        print(f"\nContainer:")
        print(f"  Status: {container.get('status', 'Unknown')}")
        print(f"  Replicas: {container.get('min_replicas', 'N/A')}-{container.get('max_replicas', 'N/A')}")
        print(f"  Created: {container.get('created_at', 'N/A')}")
        print(f"  Updated: {container.get('updated_at', 'N/A')}")
        error_msg = container.get('error_message', '')
        if error_msg:
            print(f"  Error: {error_msg}")


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
        status = get_container_status_cli()
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
    container = get_container_status_cli()
    
    # Step 1: Stop if running
    if container and container.get('status') == 'Running':
        print("\n[1/4] Stopping container...")
        try:
            stop_agent()
            # Wait for stop
            for i in range(12):
                time.sleep(10)
                status = get_container_status_cli()
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
    container = get_container_status_cli()
    if not container or container.get('status') != 'Running':
        print("Error: Container is not running.")
        print("Start it with: uv run python provision.py start")
        sys.exit(1)
    
    try:
        from azure.ai.projects.models import AgentReference
        
        client = get_client()
        
        # Get latest version
        version = get_latest_version(None, settings.agent_name)
        
        print(f"  Version: {version}")
        print(f"  Sending test message...")
        
        # Use the AIProjectClient's built-in OpenAI client
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


def check_cli_version() -> None:
    """Check that Azure CLI has the required agent commands."""
    try:
        result = subprocess.run(
            ["az", "cognitiveservices", "agent", "--help"],
            capture_output=True,
            text=True,
            shell=True,  # Required on Windows
        )
        if result.returncode != 0:
            print("Warning: Azure CLI 'az cognitiveservices agent' commands not available.")
            print("Please update Azure CLI to version 2.80.0 or later.")
            print("Run: az upgrade")
            sys.exit(1)
    except FileNotFoundError:
        print("Error: Azure CLI not found. Please install Azure CLI.")
        print("See: https://docs.microsoft.com/cli/azure/install-azure-cli")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Location Scout Agent provisioning via Azure CLI and SDK",
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

Azure CLI Commands Used:
  az cognitiveservices agent list           - List agents
  az cognitiveservices agent show           - Show agent details
  az cognitiveservices agent start          - Start container
  az cognitiveservices agent stop           - Stop container
  az cognitiveservices agent delete-deployment - Delete container

Note: Requires Azure CLI 2.80.0+ with 'az cognitiveservices agent' preview commands.
Container logs are sent to Application Insights via OpenTelemetry.
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
    
    # Check CLI version for commands that need it
    cli_commands = ["start", "stop", "restart", "redeploy", "delete-container", "list", "show", "status"]
    if args.command in cli_commands:
        check_cli_version()

    commands = {
        "deploy": deploy_foundry,
        "start": start_agent,
        "stop": stop_agent,
        "restart": restart_agent,
        "redeploy": redeploy_agent,
        "delete-container": delete_container,
        "delete": delete_agent,
        "list": list_agents,
        "show": show_status,
        "status": show_status,
        "invoke": invoke_agent,
    }

    try:
        commands[args.command]()
    except subprocess.CalledProcessError:
        # Error already printed by run_az_command
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
