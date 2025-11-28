#!/usr/bin/env python3
"""Test script to call the hosted agent via MCP protocol."""

import asyncio
import json
import httpx
from azure.identity import DefaultAzureCredential

from config import get_settings


def get_token(scope: str = "https://ai.azure.com/.default") -> str:
    """Get access token for the given scope."""
    credential = DefaultAzureCredential()
    token = credential.get_token(scope)
    return token.token


async def test_mcp_initialize():
    """Test MCP initialize handshake with the hosted agent."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 1: MCP Initialize")
    print("=" * 60)
    
    # Hosted agent MCP endpoint pattern
    # Based on the Foundry hosted agent documentation
    base_url = settings.azure_ai_foundry_endpoint
    agent_name = settings.agent_name
    version = "2"
    
    # Try different endpoint patterns
    endpoints_to_try = [
        f"{base_url}/agents/{agent_name}/versions/{version}/mcp",
        f"{base_url}/agents/{agent_name}/mcp",
    ]
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-11-15-preview"}
    
    # MCP initialize request
    mcp_init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints_to_try:
            print(f"\nTrying: {endpoint}")
            try:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    params=params,
                    json=mcp_init,
                )
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                if response.status_code == 200:
                    print("  ✓ Found working endpoint!")
                    return endpoint
            except Exception as e:
                print(f"  Error: {e}")
    
    return None


async def test_mcp_streamable_http():
    """Test MCP Streamable HTTP endpoint (POST with streaming)."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 2: MCP Streamable HTTP")
    print("=" * 60)
    
    base_url = settings.azure_ai_foundry_endpoint
    agent_name = settings.agent_name
    version = "2"
    
    # Streamable HTTP MCP endpoint patterns
    endpoints_to_try = [
        f"{base_url}/agents/{agent_name}/versions/{version}",
        f"{base_url}/agents/{agent_name}",
    ]
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    params = {"api-version": "2025-11-15-preview"}
    
    # MCP initialize with streamable HTTP
    mcp_init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint in endpoints_to_try:
            print(f"\nTrying: {endpoint}")
            try:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    params=params,
                    json=mcp_init,
                )
                print(f"  Status: {response.status_code}")
                print(f"  Headers: {dict(response.headers)}")
                print(f"  Response: {response.text[:500]}")
            except Exception as e:
                print(f"  Error: {e}")


async def test_responses_api_v1():
    """Test the responses protocol v1 (what the hosted agent supports)."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 7: Responses API v1")
    print("=" * 60)
    
    base_url = settings.azure_ai_foundry_endpoint
    agent_name = settings.agent_name
    version = "2"
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-11-15-preview"}
    
    # Try different endpoint patterns for responses API
    endpoints_to_try = [
        (f"{base_url}/agents/{agent_name}/versions/{version}:run", "run"),
        (f"{base_url}/agents/{agent_name}:run", "run"),
        (f"{base_url}/agents/{agent_name}/versions/{version}/responses", "responses"),
        (f"{base_url}/agents/{agent_name}/responses", "responses"),
        (f"{base_url}/agents/{agent_name}/versions/{version}/chat", "chat"),
        (f"{base_url}/agents/{agent_name}/chat", "chat"),
    ]
    
    # Request body
    body = {
        "input": "Hello! What can you help me with?",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for endpoint, endpoint_type in endpoints_to_try:
            print(f"\nTrying ({endpoint_type}): {endpoint}")
            try:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    params=params,
                    json=body,
                )
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text[:800]}")
                if response.status_code == 200:
                    print("  ✓ Found working endpoint!")
            except Exception as e:
                print(f"  Error: {e}")


async def test_direct_container_endpoint():
    """Test calling the container directly if it has an exposed endpoint."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 3: Direct Container Endpoint Discovery")
    print("=" * 60)
    
    # Get container details via REST API
    base_url = settings.azure_ai_foundry_endpoint
    agent_name = settings.agent_name
    version = "2"
    
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Get container info
    url = f"{base_url}/agents/{agent_name}/versions/{version}/containers/default"
    params = {"api-version": "2025-11-15-preview"}
    
    print(f"Getting container info: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Container info: {json.dumps(data, indent=2)}")
                
                # Look for endpoint URL in the response
                if "endpoint" in data:
                    print(f"\n✓ Found endpoint: {data['endpoint']}")
                if "properties" in data and "endpoint" in data["properties"]:
                    print(f"\n✓ Found endpoint: {data['properties']['endpoint']}")
            else:
                print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")


async def test_agent_as_mcp_tool():
    """Test using the agent as an MCP tool (how the orchestrator would call it)."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 4: Agent MCP Tool Call")
    print("=" * 60)
    
    # Try to use MCPStreamableHTTPTool pattern
    try:
        from agent_framework import MCPStreamableHTTPTool
        
        base_url = settings.azure_ai_foundry_endpoint
        agent_name = settings.agent_name
        version = "2"
        
        # Get token
        token = get_token()
        
        # Try different URL patterns
        url_patterns = [
            f"{base_url}/agents/{agent_name}/versions/{version}/mcp",
            f"{base_url}/agents/{agent_name}/mcp",
        ]
        
        for url in url_patterns:
            print(f"\nTrying MCPStreamableHTTPTool with: {url}")
            try:
                mcp_tool = MCPStreamableHTTPTool(
                    name=agent_name,
                    url=url,
                    headers={"Authorization": f"Bearer {token}"},
                    description="Location scout hosted agent",
                )
                
                async with mcp_tool:
                    print(f"  ✓ Connected! Available functions: {[f.name for f in mcp_tool.functions]}")
                    
                    # Try calling a function if available
                    if mcp_tool.functions:
                        print(f"\n  Functions available:")
                        for func in mcp_tool.functions:
                            print(f"    - {func.name}: {func.description[:100] if func.description else 'No description'}")
                    
            except Exception as e:
                print(f"  Error: {e}")
                
    except ImportError as e:
        print(f"Could not import MCPStreamableHTTPTool: {e}")


async def test_list_agents():
    """List all agents to see what's available."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 5: List All Agents")
    print("=" * 60)
    
    base_url = settings.azure_ai_foundry_endpoint
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-11-15-preview"}
    
    url = f"{base_url}/agents"
    print(f"Listing agents: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Agents: {json.dumps(data, indent=2)}")
            else:
                print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")


async def test_cognitiveservices_scope():
    """Test with cognitiveservices scope instead of ai.azure.com."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 6: Cognitive Services Scope Token")
    print("=" * 60)
    
    base_url = settings.azure_ai_foundry_endpoint
    agent_name = settings.agent_name
    
    # Try cognitive services scope
    token = get_token("https://cognitiveservices.azure.com/.default")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-11-15-preview"}
    
    url = f"{base_url}/agents/{agent_name}"
    print(f"Getting agent with cognitiveservices scope: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {e}")


async def test_invoke_via_openai_sdk():
    """Test invoking the hosted agent via OpenAI SDK as documented."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 8: Invoke via OpenAI SDK (Documented Method)")
    print("=" * 60)
    
    from azure.identity import DefaultAzureCredential
    from azure.ai.projects import AIProjectClient
    
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=credential,
    )
    
    agent_name = settings.agent_name
    agent_version = "2"
    
    print(f"Agent: {agent_name}")
    print(f"Version: {agent_version}")
    print(f"Endpoint: {settings.azure_ai_foundry_endpoint}")
    
    try:
        # Get OpenAI client
        print("\nGetting OpenAI client...")
        openai_client = client.get_openai_client()
        print(f"Got OpenAI client: {type(openai_client)}")
        
        # Check if responses exists
        if hasattr(openai_client, 'responses'):
            print("responses attribute found")
            
            # Create response using the agent
            print("\nCalling responses.create with agent reference...")
            response = openai_client.responses.create(
                input=[{"role": "user", "content": "Hello! What can you help me with?"}],
                extra_body={"agent": {"name": agent_name, "version": agent_version}}
            )
            
            print("Success!")
            print(f"Response type: {type(response)}")
            if hasattr(response, 'output_text'):
                print(f"Output: {response.output_text}")
            else:
                print(f"Response: {response}")
        else:
            print("No responses attribute on OpenAI client")
            
            # Try chat completions with model override
            print("\nTrying chat.completions with model override...")
            response = openai_client.chat.completions.create(
                model=f"agents/{agent_name}",
                messages=[{"role": "user", "content": "Hello!"}],
                max_completion_tokens=100,
            )
            print(f"Success! Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    await test_list_agents()
    await test_cognitiveservices_scope()
    await test_direct_container_endpoint()
    await test_invoke_via_openai_sdk()
    # await test_responses_api_v1()
    # await test_mcp_initialize()
    # await test_mcp_streamable_http()
    # await test_agent_as_mcp_tool()


if __name__ == "__main__":
    asyncio.run(main())
