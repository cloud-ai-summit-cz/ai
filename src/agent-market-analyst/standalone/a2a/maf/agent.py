"""Market Analyst Agent using Microsoft Agent Framework.

This module implements the Market Analyst agent using AzureOpenAIResponsesClient
from the Microsoft Agent Framework.
"""

import asyncio
from typing import Optional

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from config import Settings


class MarketAnalystAgent:
    """Market Analyst Agent powered by Microsoft Agent Framework.

    This agent specializes in market analysis for the specialty coffee
    and hospitality industry, helping Cofilot evaluate expansion opportunities.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize the Market Analyst Agent.

        Args:
            settings: Configuration settings. If None, loads from environment.
        """
        self._settings = settings or Settings()
        self._agent = None

    @property
    def system_prompt(self) -> str:
        """Load the system prompt from file."""
        return self._settings.get_system_prompt()

    async def initialize(self) -> None:
        """Initialize the agent with Azure OpenAI connection."""
        if self._agent is not None:
            return

        # DefaultAzureCredential works with:
        # - Azure CLI locally (az login)
        # - Managed Identity in Azure containers
        # - Environment variables, VS Code, etc.
        #
        # Note: For cognitiveservices.azure.com endpoints, we must explicitly
        # set base_url to include /openai/v1/ path for Responses API
        self._agent = AzureOpenAIResponsesClient(
            credential=DefaultAzureCredential(),
            endpoint=self._settings.azure_openai_endpoint,
            base_url=self._settings.azure_openai_base_url,
            deployment_name=self._settings.model_deployment_name,
            api_version=self._settings.azure_openai_api_version,
        ).create_agent(
            instructions=self.system_prompt,
        )

    async def run(self, message: str) -> str:
        """Run the agent with a user message and return the response.

        Args:
            message: The user's input message.

        Returns:
            The agent's response text.
        """
        if self._agent is None:
            await self.initialize()

        result = await self._agent.run(message)
        return result.text

    async def run_stream(self, message: str):
        """Run the agent with streaming response.

        Args:
            message: The user's input message.

        Yields:
            Chunks of the agent's response.
        """
        if self._agent is None:
            await self.initialize()

        async for chunk in self._agent.run_stream(message):
            if chunk.text:
                yield chunk.text

    async def close(self) -> None:
        """Clean up resources."""
        self._agent = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def main():
    """Example usage of the Market Analyst Agent."""
    async with MarketAnalystAgent() as agent:
        response = await agent.run(
            "What is the estimated market size for specialty coffee in Brno, Czech Republic?"
        )
        print(f"Agent: {response}")


if __name__ == "__main__":
    asyncio.run(main())
