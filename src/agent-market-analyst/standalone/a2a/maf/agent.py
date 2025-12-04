"""Market Analyst Agent using Microsoft Agent Framework.

This module implements the Market Analyst agent using AzureOpenAIResponsesClient
from the Microsoft Agent Framework with MCP tool integration for demographics data.
"""

import asyncio
import logging
from typing import Optional

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from config import Settings

logger = logging.getLogger(__name__)


class MarketAnalystAgent:
    """Market Analyst Agent powered by Microsoft Agent Framework.

    This agent specializes in market analysis for the specialty coffee
    and hospitality industry, helping Cofilot evaluate expansion opportunities.
    Uses MCP Demographics tool for real demographic data.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize the Market Analyst Agent.

        Args:
            settings: Configuration settings. If None, loads from environment.
        """
        self._settings = settings or Settings()
        self._agent: ChatAgent | None = None
        self._mcp_tool: MCPStreamableHTTPTool | None = None

    @property
    def system_prompt(self) -> str:
        """Load the system prompt from file."""
        return self._settings.get_system_prompt()

    async def initialize(self) -> None:
        """Initialize the agent with Azure OpenAI connection and MCP tools."""
        if self._agent is not None:
            return

        logger.info("=" * 60)
        logger.info("[INIT] Initializing Market Analyst Agent")
        logger.info(f"[INIT] Azure OpenAI Endpoint: {self._settings.azure_openai_endpoint}")
        logger.info(f"[INIT] Model: {self._settings.model_deployment_name}")
        
        # Create MCP Demographics tool with authentication
        logger.info(f"[MCP INIT] Connecting to MCP Demographics server...")
        logger.info(f"[MCP INIT] URL: {self._settings.mcp_demographics_url}")
        self._mcp_tool = MCPStreamableHTTPTool(
            name="demographics",
            url=self._settings.mcp_demographics_url,
            description="Demographic and consumer behavior data for market analysis",
            headers={"Authorization": f"Bearer {self._settings.mcp_demographics_api_key}"},
        )

        # Connect to the MCP server
        await self._mcp_tool.__aenter__()
        
        # Log available MCP tools
        if self._mcp_tool.functions:
            tool_names = [f.name for f in self._mcp_tool.functions]
            logger.info(f"[MCP INIT] Connection successful! {len(tool_names)} tools available:")
            for name in tool_names:
                logger.info(f"[MCP INIT]   - {name}")
        else:
            logger.warning("[MCP INIT] Connected but no tools were loaded!")

        # DefaultAzureCredential works with:
        # - Azure CLI locally (az login)
        # - Managed Identity in Azure containers
        # - Environment variables, VS Code, etc.
        #
        # Note: For cognitiveservices.azure.com endpoints, we must explicitly
        # set base_url to include /openai/v1/ path for Responses API
        logger.info("[INIT] Creating Azure OpenAI Responses client...")
        responses_client = AzureOpenAIResponsesClient(
            credential=DefaultAzureCredential(),
            endpoint=self._settings.azure_openai_endpoint,
            base_url=self._settings.azure_openai_base_url,
            deployment_name=self._settings.model_deployment_name,
            api_version=self._settings.azure_openai_api_version,
        )

        self._agent = responses_client.create_agent(
            instructions=self.system_prompt,
            tools=[self._mcp_tool],
        )
        logger.info("[INIT] Agent initialized successfully!")
        logger.info("=" * 60)

    async def run(self, message: str) -> str:
        """Run the agent with a user message and return the response.

        Args:
            message: The user's input message.

        Returns:
            The agent's response text.
        """
        if self._agent is None:
            await self.initialize()

        # Log input (first 150 chars)
        input_preview = message[:150] + "..." if len(message) > 150 else message
        logger.info(f"[INPUT] User message: {input_preview}")
        
        result = await self._agent.run(message)
        
        # Log MCP tool calls if any were made
        if hasattr(result, 'tool_calls') and result.tool_calls:
            logger.info(f"[MCP] {len(result.tool_calls)} tool call(s) made")
            for i, tool_call in enumerate(result.tool_calls, 1):
                logger.info(f"[MCP CALL {i}] Tool: {tool_call.name}")
                # Log tool input (first 200 chars)
                args_str = str(tool_call.arguments) if tool_call.arguments else "{}"
                args_preview = args_str[:200] + "..." if len(args_str) > 200 else args_str
                logger.info(f"[MCP CALL {i}] Input: {args_preview}")
                # Log tool output (first 300 chars)
                if tool_call.result:
                    result_str = str(tool_call.result)
                    result_preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
                    logger.info(f"[MCP CALL {i}] Output: {result_preview}")
                else:
                    logger.info(f"[MCP CALL {i}] Output: None")
        else:
            logger.info("[MCP] No tool calls made for this request")
        
        # Log output (first 200 chars)
        output_preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
        logger.info(f"[OUTPUT] Agent response ({len(result.text)} chars): {output_preview}")
        
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
        if self._mcp_tool is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Demographics server...")
            await self._mcp_tool.__aexit__(None, None, None)
            self._mcp_tool = None
            logger.info("[SHUTDOWN] MCP connection closed")
        self._agent = None
        logger.info("[SHUTDOWN] Agent resources released")

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
