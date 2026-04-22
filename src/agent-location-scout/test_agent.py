#!/usr/bin/env python3
"""Test script to call the hosted agent and debug RBAC issues."""

import json
import sys
import requests

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from config import get_settings


def get_token(scope: str = "https://cognitiveservices.azure.com/.default") -> str:
    """Get access token for the given scope."""
    credential = DefaultAzureCredential()
    token = credential.get_token(scope)
    return token.token


def test_openai_direct():
    """Test calling Azure OpenAI directly to verify permissions."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 1: Direct Azure OpenAI Call")
    print("=" * 60)
    
    # Extract account endpoint from foundry endpoint
    # https://ncus-foundry-hosting-resource.services.ai.azure.com/api/projects/ncus-foundry-hosting
    # -> https://ncus-foundry-hosting-resource.openai.azure.com/
    endpoint_parts = settings.azure_ai_foundry_endpoint.split("/")
    account_host = endpoint_parts[2]  # ncus-foundry-hosting-resource.services.ai.azure.com
    account_name = account_host.split(".")[0]  # ncus-foundry-hosting-resource
    
    openai_endpoint = f"https://{account_name}.openai.azure.com"
    print(f"OpenAI Endpoint: {openai_endpoint}")
    print(f"Model: {settings.azure_openai_deployment}")
    
    token = get_token()
    
    url = f"{openai_endpoint}/openai/deployments/{settings.azure_openai_deployment}/chat/completions?api-version=2024-02-15-preview"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_completion_tokens": 50,
    }
    
    print(f"\nCalling: {url}")
    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success! Response: {result['choices'][0]['message']['content']}")
        else:
            print(f"✗ Failed: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_hosted_agent_api():
    """Test calling the hosted agent via REST API."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 2: Hosted Agent REST API")
    print("=" * 60)
    
    # Get the data plane base URL
    endpoint = settings.azure_ai_foundry_endpoint
    # https://ncus-foundry-hosting-resource.services.ai.azure.com/api/projects/ncus-foundry-hosting
    base_url = endpoint  # The endpoint IS the base URL for the project
    
    print(f"Base URL: {base_url}")
    print(f"Agent: {settings.agent_name}")
    
    # Use ai.azure.com scope for agent API
    token = get_token("https://ai.azure.com/.default")
    
    # Create a session/thread with the agent
    url = f"{base_url}/agents/{settings.agent_name}/versions/2/sessions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-05-15-preview"}
    
    print(f"\nCreating session: {url}")
    try:
        response = requests.post(url, headers=headers, params=params, json={}, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            session = response.json()
            session_id = session.get("id")
            print(f"✓ Session created: {session_id}")
            
            # Send a message
            msg_url = f"{base_url}/agents/{settings.agent_name}/versions/2/sessions/{session_id}/messages"
            msg_body = {
                "role": "user",
                "content": "Hello, what can you help me with?",
            }
            print(f"\nSending message: {msg_url}")
            msg_response = requests.post(msg_url, headers=headers, params=params, json=msg_body, timeout=60)
            print(f"Status: {msg_response.status_code}")
            print(f"Response: {msg_response.text[:500]}")
        else:
            print(f"✗ Failed to create session")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


def test_responses_api():
    """Test calling the agent using the responses API pattern."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 3: Agent Responses API")
    print("=" * 60)
    
    base_url = settings.azure_ai_foundry_endpoint
    print(f"Base URL: {base_url}")
    print(f"Agent: {settings.agent_name}")
    
    token = get_token("https://ai.azure.com/.default")
    
    # Try the responses endpoint pattern
    url = f"{base_url}/agents/{settings.agent_name}:run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"api-version": "2025-05-15-preview"}
    body = {
        "input": "Hello, what can you help me with?",
    }
    
    print(f"\nCalling: {url}")
    try:
        response = requests.post(url, headers=headers, params=params, json=body, timeout=60)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:1000]}")
    except Exception as e:
        print(f"✗ Error: {e}")


def test_sdk_openai():
    """Test using the SDK's get_openai_client."""
    settings = get_settings()
    
    print("\n" + "=" * 60)
    print("Test 4: SDK OpenAI Client")
    print("=" * 60)
    
    credential = DefaultAzureCredential()
    client = AIProjectClient(
        endpoint=settings.azure_ai_foundry_endpoint,
        credential=credential,
    )
    
    print("Getting OpenAI client...")
    try:
        openai_client = client.get_openai_client()
        print(f"✓ Got OpenAI client: {type(openai_client)}")
        
        print(f"\nCalling chat completions with model: {settings.azure_openai_deployment}")
        response = openai_client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": "Say hello"}],
            max_completion_tokens=50,
        )
        print(f"✓ Success! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_openai_direct()
    test_sdk_openai()
    test_hosted_agent_api()
    test_responses_api()
