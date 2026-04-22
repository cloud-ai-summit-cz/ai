#!/usr/bin/env python
"""
Provision script for Test Hosted Agent.

Manages Azure AI Foundry hosted agent deployment.
Simplified version focusing on deploy/start/stop/status/invoke.

Commands:
    deploy  - Create/update hosted agent version
    start   - Start the hosted agent container
    stop    - Stop the hosted agent container
    status  - Show container status
    invoke  - Test invoke the agent

Requires:
    - Azure CLI 2.80.0+ with `az cognitiveservices agent` preview commands
    - azure-ai-projects Python SDK
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ImageBasedHostedAgentDefinition,
    ProtocolVersionRecord,
    AgentProtocol,
)

from config import get_settings

load_dotenv()


def run_az_command(args: list[str], check: bool = True) -> dict[str, Any] | list[Any] | None:
    """Run an Azure CLI command and return parsed JSON output."""
    cmd = ["az"] + args + ["--output", "json"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            shell=True,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running: az {' '.join(args)}")
            if e.stderr:
                print(f"  Error: {e.stderr}")
            raise
        return None
    except json.JSONDecodeError:
        return None


def get_client() -> AIProjectClient:
    """Create AIProjectClient."""
    settings = get_settings()
    credential = DefaultAzureCredential()
    return AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=credential,
    )


def parse_endpoint(endpoint: str) -> tuple[str, str]:
    """Parse Foundry endpoint to get account and project names."""
    match = re.match(
        r"https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)",
        endpoint
    )
    if match:
        return match.group(1), match.group(2)
    raise ValueError(f"Cannot parse endpoint: {endpoint}")


def get_agent_versions_cli(agent_name: str) -> list[dict] | None:
    """Get all versions of an agent."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    return run_az_command([
        "cognitiveservices", "agent", "list-versions",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", agent_name,
    ], check=False)


def get_latest_version(agent_name: str) -> str:
    """Get the latest version number for an agent."""
    versions = get_agent_versions_cli(agent_name)
    if not versions:
        return "1"
    try:
        sorted_versions = sorted(
            versions, 
            key=lambda v: int(v.get('version', '0')), 
            reverse=True
        )
        if sorted_versions:
            return sorted_versions[0].get('version', '1')
    except ValueError:
        pass
    return "1"


def get_container_status_cli() -> dict | None:
    """Get container status."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    version = get_latest_version(settings.agent_name)
    
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


def deploy_foundry() -> None:
    """Deploy the agent to Azure AI Foundry."""
    settings = get_settings()
    client = get_client()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)

    print(f"Deploying hosted agent: {settings.agent_name}")
    print(f"  Container image: {settings.container_image}")
    print(f"  Account: {account_name}, Project: {project_name}")

    # Check if agent exists
    existing = get_agent_versions_cli(settings.agent_name)
    if existing:
        print("  Agent exists, creating new version...")

    # Build cognitiveservices endpoint
    azure_openai_endpoint = f"https://{account_name}.cognitiveservices.azure.com"
    
    # Using token-based auth (DefaultAzureCredential) - NO API KEY NEEDED
    # The container's managed identity will get tokens automatically
    
    # Environment variables - for AzureChatOpenAI with token provider
    env_vars = {
        "AZURE_OPENAI_ENDPOINT": azure_openai_endpoint,
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": settings.azure_openai_deployment,
        "OPENAI_API_VERSION": "2024-10-21",
    }
    
    print(f"  ✓ Using managed identity auth (no API key)")
    
    # Add tenant ID if set
    tenant_id = os.getenv("AZURE_TENANT_ID")
    if tenant_id:
        env_vars["AZURE_TENANT_ID"] = tenant_id
    
    # Add App Insights if available
    app_insights = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if app_insights:
        env_vars["APPLICATIONINSIGHTS_CONNECTION_STRING"] = app_insights

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
    
    print(f"✓ Agent version created: {result.version}")
    print(f"\nNow run: uv run python provision.py start")


def start_agent() -> None:
    """Start the hosted agent container."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    version = get_latest_version(settings.agent_name)
    
    print(f"Starting: {settings.agent_name} (version {version})")
    
    result = run_az_command([
        "cognitiveservices", "agent", "start",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ])
    
    if result:
        print(f"✓ Start command sent")
    
    # Poll for status
    print("Waiting for container...")
    for i in range(30):
        time.sleep(10)
        status = get_container_status_cli()
        if status:
            container_status = status.get('status', 'Unknown')
            print(f"  [{i+1}] Status: {container_status}")
            
            if container_status == "Running":
                print("\n✓ Container is running!")
                return
            elif container_status in ["Failed", "Stopped"]:
                error = status.get('error_message', '')
                print(f"\n✗ Failed: {container_status}")
                if error:
                    print(f"  Error: {error}")
                sys.exit(1)
    
    print("\n⚠ Still starting. Check with: uv run python provision.py status")


def stop_agent() -> None:
    """Stop the hosted agent container."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    version = get_latest_version(settings.agent_name)
    
    print(f"Stopping: {settings.agent_name} (version {version})")
    
    run_az_command([
        "cognitiveservices", "agent", "stop",
        "--account-name", account_name,
        "--project-name", project_name,
        "--name", settings.agent_name,
        "--agent-version", version,
    ])
    
    print("✓ Stop command sent")


def show_status() -> None:
    """Show current status."""
    settings = get_settings()
    account_name, project_name = parse_endpoint(settings.azure_ai_foundry_endpoint)
    
    print(f"Test Hosted Agent")
    print("=" * 50)
    print(f"Agent Name: {settings.agent_name}")
    print(f"Image:      {settings.container_image}")
    print(f"Model:      {settings.azure_openai_deployment}")
    print(f"Account:    {account_name}")
    print(f"Project:    {project_name}")
    print("-" * 50)
    
    # Get versions
    versions = get_agent_versions_cli(settings.agent_name)
    if versions:
        version = get_latest_version(settings.agent_name)
        print(f"Latest Version: {version}")
        
        container = get_container_status_cli()
        if container:
            print(f"Container Status: {container.get('status', 'Unknown')}")
            error = container.get('error_message', '')
            if error:
                print(f"Error: {error}")
        else:
            print("Container: Not deployed")
    else:
        print("Agent: Not deployed")


def invoke_agent() -> None:
    """Test invoke the agent."""
    settings = get_settings()
    
    print(f"Invoking: {settings.agent_name}")
    print("-" * 40)
    
    # Check container status
    container = get_container_status_cli()
    if not container or container.get('status') != 'Running':
        print("Error: Container not running")
        sys.exit(1)
    
    try:
        from azure.ai.projects.models import AgentReference
        
        client = get_client()
        version = get_latest_version(settings.agent_name)
        
        print(f"  Version: {version}")
        print("  Sending test message...")
        
        openai_client = client.get_openai_client()
        agent_ref = AgentReference(name=settings.agent_name, version=version)
        
        response = openai_client.responses.create(
            input=[{"role": "user", "content": "What is 3 + 5?"}],
            extra_body={"agent": agent_ref.as_dict()}
        )
        
        print(f"\n  Response Status: {response.status}")
        print(f"  Full response: {response}")
        
        if response.error:
            print(f"  Error Code: {response.error.code}")
            print(f"  Error Message: {response.error.message}")
        elif hasattr(response, 'output_text') and response.output_text:
            print(f"\n  Agent Response:")
            print(f"  {response.output_text}")
        else:
            print(f"\n  Output: {response.output}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Hosted Agent provisioning"
    )
    parser.add_argument(
        "command",
        choices=["deploy", "start", "stop", "status", "invoke"],
        help="Command to execute",
    )

    args = parser.parse_args()
    
    commands = {
        "deploy": deploy_foundry,
        "start": start_agent,
        "stop": stop_agent,
        "status": show_status,
        "invoke": invoke_agent,
    }

    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
