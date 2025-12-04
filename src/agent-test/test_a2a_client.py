"""Test client for the Market Analyst A2A Agent.

This script connects to the Market Analyst agent via the A2A protocol
and sends test queries to verify the agent is working correctly.
"""

import asyncio
import os

import httpx
from a2a.types import AgentCard
from agent_framework.a2a import A2AAgent
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def main():
    """Test the Market Analyst A2A agent with sample queries."""
    # Get A2A agent card URL and API key from environment
    agent_card_url = os.getenv(
        "A2A_AGENT_CARD_URL", 
        "http://localhost:8020/.well-known/agent-card.json"
    )
    a2a_api_key = os.getenv("A2A_API_KEY", "")

    print("=" * 70)
    print("Market Analyst A2A Agent Test Client")
    print("=" * 70)
    print(f"\nAgent Card URL: {agent_card_url}")
    if a2a_api_key:
        print("Using API key authentication")
    else:
        print("No API key configured (server may reject requests)")

    # Set up headers for authentication
    headers = {}
    if a2a_api_key:
        headers["Authorization"] = f"Bearer {a2a_api_key}"

    # Initialize HTTP client
    async with httpx.AsyncClient(timeout=120.0, headers=headers) as http_client:
        # Step 1: Fetch the Agent Card directly from the well-known URL
        print("\n[1] Fetching Agent Card...")
        try:
            response = await http_client.get(agent_card_url)
            response.raise_for_status()
            agent_card = AgentCard.model_validate(response.json())
            
            print(f"    ✓ Found agent: {agent_card.name}")
            print(f"    ✓ Description: {agent_card.description}")
            print(f"    ✓ Version: {agent_card.version}")
            print(f"    ✓ Agent URL: {agent_card.url}")
            
            if agent_card.skills:
                print(f"    ✓ Skills: {len(agent_card.skills)}")
                for skill in agent_card.skills:
                    print(f"      - {skill.name}: {skill.description[:60]}...")
            
            # Check if authentication is required
            if agent_card.security_schemes:
                print(f"    ✓ Security: {list(agent_card.security_schemes.keys())}")
        except httpx.HTTPStatusError as e:
            print(f"    ✗ HTTP error fetching Agent Card: {e.response.status_code}")
            print(f"      {e.response.text[:200]}")
            return
        except Exception as e:
            print(f"    ✗ Failed to fetch Agent Card: {e}")
            print("\n    Make sure the Market Analyst A2A server is running:")
            print("    cd src/agent-market-analyst/standalone/a2a/maf")
            print("    uv run python main.py")
            return

        # Step 2: Create A2A agent instance using the URL from the Agent Card
        print("\n[2] Creating A2A agent instance...")
        
        # Extract base URL from agent card (remove trailing slash for consistency)
        agent_url = agent_card.url.rstrip("/") if agent_card.url else agent_card_url.rsplit("/.well-known", 1)[0]
        
        agent = A2AAgent(
            name=agent_card.name,
            description=agent_card.description,
            agent_card=agent_card,
            url=agent_url,
            http_client=http_client,
        )
        print(f"    ✓ A2A agent created (URL: {agent_url})")

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
