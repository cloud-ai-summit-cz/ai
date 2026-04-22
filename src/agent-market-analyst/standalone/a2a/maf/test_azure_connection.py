"""Quick test to verify Azure OpenAI connection works."""

import asyncio
from azure.identity import DefaultAzureCredential
from agent_framework.azure import AzureOpenAIResponsesClient

from config import get_settings


async def main():
    settings = get_settings()
    
    print("Testing Azure OpenAI Connection")
    print("=" * 50)
    print(f"Endpoint: {settings.azure_openai_endpoint}")
    print(f"Base URL: {settings.azure_openai_base_url}")
    print(f"Model: {settings.model_deployment_name}")
    print(f"API Version: {settings.azure_openai_api_version}")
    print("=" * 50)
    
    try:
        print("\nCreating client...")
        client = AzureOpenAIResponsesClient(
            credential=DefaultAzureCredential(),
            endpoint=settings.azure_openai_endpoint,
            base_url=settings.azure_openai_base_url,
            deployment_name=settings.model_deployment_name,
            api_version=settings.azure_openai_api_version,
        )
        
        print("Creating agent...")
        agent = client.create_agent(
            instructions="You are a helpful assistant. Answer briefly.",
        )
        
        print("Sending test message...")
        result = await agent.run("What is 2+2? Answer with just the number.")
        
        print(f"\n✓ Success! Response: {result.text}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
