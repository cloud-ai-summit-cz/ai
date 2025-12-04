"""Test client for the Market Analyst A2A Agent.

This script connects to the Market Analyst agent via the A2A protocol
and sends test queries to verify the agent is working correctly.
"""

import asyncio
import os

import httpx
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def main():
    """Test the Market Analyst A2A agent with sample queries."""
    # Get A2A agent host and API key from environment or use defaults
    a2a_agent_host = os.getenv("A2A_AGENT_HOST", "http://localhost:8020")
    a2a_api_key = os.getenv("A2A_API_KEY", "")

    print("=" * 70)
    print("Market Analyst A2A Agent Test Client")
    print("=" * 70)
    print(f"\nConnecting to A2A agent at: {a2a_agent_host}")
    if a2a_api_key:
        print("Using API key authentication")
    else:
        print("No API key configured (server may reject requests)")

    # Set up headers for authentication
    headers = {}
    if a2a_api_key:
        headers["Authorization"] = f"Bearer {a2a_api_key}"

    # Initialize HTTP client and A2A card resolver
    async with httpx.AsyncClient(timeout=120.0, headers=headers) as http_client:
        resolver = A2ACardResolver(httpx_client=http_client, base_url=a2a_agent_host)

        # Step 1: Discover the agent via AgentCard
        print("\n[1] Discovering agent...")
        try:
            agent_card = await resolver.get_agent_card()
            print(f"    ✓ Found agent: {agent_card.name}")
            print(f"    ✓ Description: {agent_card.description}")
            print(f"    ✓ Version: {agent_card.version}")
            
            if agent_card.skills:
                print(f"    ✓ Skills: {len(agent_card.skills)}")
                for skill in agent_card.skills:
                    print(f"      - {skill.name}: {skill.description[:60]}...")
        except Exception as e:
            print(f"    ✗ Failed to discover agent: {e}")
            print("\n    Make sure the Market Analyst A2A server is running:")
            print("    cd src/agent-market-analyst/standalone/a2a/maf")
            print("    uv run python main.py")
            return

        # Step 2: Create A2A agent instance
        print("\n[2] Creating A2A agent instance...")
        agent = A2AAgent(
            name=agent_card.name,
            description=agent_card.description,
            agent_card=agent_card,
            url=a2a_agent_host,
            http_client=http_client,
        )
        print("    ✓ A2A agent created")

        # Step 3: Send test queries
        test_queries = [
            "What is the estimated market size for specialty coffee in Brno, Czech Republic?",
            # "What are the key customer segments for third-wave coffee shops?",
            # "What trends are driving growth in the specialty coffee market?",
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"\n[3.{i}] Testing query...")
            print(f"    Query: {query[:70]}...")
            print("\n    Sending to agent...")

            try:
                response = await agent.run(query)
                
                print("\n    ✓ Response received!")
                print("\n" + "-" * 70)
                print("AGENT RESPONSE:")
                print("-" * 70)
                
                for message in response.messages:
                    if message.text:
                        # Print first 1000 chars of response
                        text = message.text
                        if len(text) > 1000:
                            print(text[:1000] + "\n... [truncated]")
                        else:
                            print(text)
                
                print("-" * 70)

            except Exception as e:
                print(f"    ✗ Error: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
