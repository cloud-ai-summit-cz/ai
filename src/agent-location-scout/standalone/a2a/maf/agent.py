"""Location Scout Agent using Microsoft Agent Framework.

This module implements the Location Scout agent using AzureOpenAIResponsesClient
from the Microsoft Agent Framework with MCP tool integration for government data,
demographics, real estate data, and grounded web search for location analysis.
"""

import asyncio
import logging
from typing import Optional

from agent_framework import ChatAgent, HostedWebSearchTool, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from config import Settings

logger = logging.getLogger(__name__)

# MCP connection timeout configuration
# Longer timeouts to handle Azure API Management and TLS handshake latency
MCP_CONNECTION_TIMEOUT = 60.0  # 60 seconds for initial connection/TLS handshake
MCP_SSE_READ_TIMEOUT = 120.0  # 120 seconds for SSE stream reads (tool execution)
MCP_REQUEST_TIMEOUT = 90  # 90 seconds for individual MCP requests


class LocationScoutAgent:
    """Location Scout Agent powered by Microsoft Agent Framework.

    This agent specializes in commercial real estate and business location analysis
    for the specialty coffee and hospitality industry, helping Cofilot evaluate
    expansion opportunities in Brno and Vienna.
    Uses MCP Government Data for permits and regulations, MCP Demographics for
    population data and foot traffic, MCP Real Estate for property listings,
    and MCP Scratchpad for session-scoped collaboration with other agents.
    Uses Grounded Web Search (Bing) for real-time location intelligence.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Initialize the Location Scout Agent.

        Args:
            settings: Configuration settings. If None, loads from environment.
            session_id: Optional session ID for session-scoped MCP tools.
                       When provided, enables collaboration via MCP Scratchpad.
        """
        self._settings = settings or Settings()
        self._session_id = session_id
        self._agent: ChatAgent | None = None
        self._mcp_government_data: MCPStreamableHTTPTool | None = None
        self._mcp_demographics: MCPStreamableHTTPTool | None = None
        self._mcp_real_estate: MCPStreamableHTTPTool | None = None
        self._mcp_scratchpad: MCPStreamableHTTPTool | None = None

    @property
    def system_prompt(self) -> str:
        """Load the system prompt from file."""
        return self._settings.get_system_prompt()

    async def initialize(self) -> None:
        """Initialize the agent with Azure OpenAI connection and MCP tools."""
        if self._agent is not None:
            return

        logger.info("=" * 60)
        logger.info("[INIT] Initializing Location Scout Agent")
        logger.info(f"[INIT] Azure OpenAI Endpoint: {self._settings.azure_openai_endpoint}")
        logger.info(f"[INIT] Model: {self._settings.model_deployment_name}")
        if self._session_id:
            logger.info(f"[INIT] Session ID: {self._session_id}")
        
        # List to collect MCP tools
        mcp_tools = []
        
        # Create MCP Government Data tool (permits, regulations, zoning)
        logger.info(f"[MCP INIT] Connecting to MCP Government Data server...")
        logger.info(f"[MCP INIT] URL: {self._settings.mcp_government_data_url}")
        self._mcp_government_data = MCPStreamableHTTPTool(
            name="government_data",
            url=self._settings.mcp_government_data_url,
            description="Government data for permits, licenses, regulations, zoning requirements, and compliance",
            headers={"Authorization": f"Bearer {self._settings.mcp_government_data_api_key}"},
            timeout=MCP_CONNECTION_TIMEOUT,
            sse_read_timeout=MCP_SSE_READ_TIMEOUT,
            request_timeout=MCP_REQUEST_TIMEOUT,
        )
        await self._mcp_government_data.__aenter__()
        if self._mcp_government_data.functions:
            tool_names = [f.name for f in self._mcp_government_data.functions]
            logger.info(f"[MCP INIT] Government Data connection successful! {len(tool_names)} tools available:")
            for name in tool_names:
                logger.info(f"[MCP INIT]   - {name}")
        else:
            logger.warning("[MCP INIT] Government Data connected but no tools were loaded!")
        mcp_tools.append(self._mcp_government_data)
        
        # Create MCP Demographics tool (population, income, foot traffic)
        logger.info(f"[MCP INIT] Connecting to MCP Demographics server...")
        logger.info(f"[MCP INIT] URL: {self._settings.mcp_demographics_url}")
        self._mcp_demographics = MCPStreamableHTTPTool(
            name="demographics",
            url=self._settings.mcp_demographics_url,
            description="Demographics data for population density, age distribution, income levels, foot traffic patterns",
            headers={"Authorization": f"Bearer {self._settings.mcp_demographics_api_key}"},
            timeout=MCP_CONNECTION_TIMEOUT,
            sse_read_timeout=MCP_SSE_READ_TIMEOUT,
            request_timeout=MCP_REQUEST_TIMEOUT,
        )
        await self._mcp_demographics.__aenter__()
        if self._mcp_demographics.functions:
            tool_names = [f.name for f in self._mcp_demographics.functions]
            logger.info(f"[MCP INIT] Demographics connection successful! {len(tool_names)} tools available:")
            for name in tool_names:
                logger.info(f"[MCP INIT]   - {name}")
        else:
            logger.warning("[MCP INIT] Demographics connected but no tools were loaded!")
        mcp_tools.append(self._mcp_demographics)
        
        # Create MCP Real Estate tool (property listings, rental rates)
        logger.info(f"[MCP INIT] Connecting to MCP Real Estate server...")
        logger.info(f"[MCP INIT] URL: {self._settings.mcp_real_estate_url}")
        self._mcp_real_estate = MCPStreamableHTTPTool(
            name="real_estate",
            url=self._settings.mcp_real_estate_url,
            description="Real estate data for property listings, rental rates, commercial space availability, lease terms",
            headers={"Authorization": f"Bearer {self._settings.mcp_real_estate_api_key}"},
            timeout=MCP_CONNECTION_TIMEOUT,
            sse_read_timeout=MCP_SSE_READ_TIMEOUT,
            request_timeout=MCP_REQUEST_TIMEOUT,
        )
        await self._mcp_real_estate.__aenter__()
        if self._mcp_real_estate.functions:
            tool_names = [f.name for f in self._mcp_real_estate.functions]
            logger.info(f"[MCP INIT] Real Estate connection successful! {len(tool_names)} tools available:")
            for name in tool_names:
                logger.info(f"[MCP INIT]   - {name}")
        else:
            logger.warning("[MCP INIT] Real Estate connected but no tools were loaded!")
        mcp_tools.append(self._mcp_real_estate)
        
        # Create MCP Scratchpad tool with session scope (if session_id provided)
        if self._session_id:
            logger.info(f"[MCP INIT] Connecting to MCP Scratchpad server...")
            logger.info(f"[MCP INIT] URL: {self._settings.mcp_scratchpad_url}")
            logger.info(f"[MCP INIT] Session ID: {self._session_id}")
            
            # Headers for session-scoped access
            scratchpad_headers = {
                "Authorization": f"Bearer {self._settings.mcp_scratchpad_api_key}",
                "X-Session-ID": self._session_id,
                "X-Caller-Agent": "location-scout",
            }
            
            self._mcp_scratchpad = MCPStreamableHTTPTool(
                name="scratchpad",
                url=self._settings.mcp_scratchpad_url,
                description="Shared scratchpad for session-scoped collaboration with other agents. Use to read findings from other agents and write your own location analysis.",
                headers=scratchpad_headers,
                timeout=MCP_CONNECTION_TIMEOUT,
                sse_read_timeout=MCP_SSE_READ_TIMEOUT,
                request_timeout=MCP_REQUEST_TIMEOUT,
            )
            
            # Connect to the MCP Scratchpad server
            await self._mcp_scratchpad.__aenter__()
            
            # Log available tools
            if self._mcp_scratchpad.functions:
                tool_names = [f.name for f in self._mcp_scratchpad.functions]
                logger.info(f"[MCP INIT] Scratchpad connection successful! {len(tool_names)} tools available:")
                for name in tool_names:
                    logger.info(f"[MCP INIT]   - {name}")
            else:
                logger.warning("[MCP INIT] Scratchpad connected but no tools were loaded!")
            mcp_tools.append(self._mcp_scratchpad)
        else:
            logger.info("[MCP INIT] No session ID - scratchpad tool not enabled")

        # Add web search tool (Grounded with Bing) for real-time location data
        logger.info("[TOOL INIT] Adding web search capability (Grounding with Bing)...")
        web_search_tool = HostedWebSearchTool(
            description="Search the web for current location data, real estate listings, neighborhood trends, and local regulations",
        )
        mcp_tools.append(web_search_tool)
        logger.info("[TOOL INIT] Web search tool added")

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
            tools=mcp_tools,
        )
        logger.info(f"[INIT] Agent initialized successfully with {len(mcp_tools)} MCP tool(s)!")
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
        if self._mcp_scratchpad is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Scratchpad server...")
            await self._mcp_scratchpad.__aexit__(None, None, None)
            self._mcp_scratchpad = None
            logger.info("[SHUTDOWN] MCP Scratchpad connection closed")
        if self._mcp_real_estate is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Real Estate server...")
            await self._mcp_real_estate.__aexit__(None, None, None)
            self._mcp_real_estate = None
            logger.info("[SHUTDOWN] MCP Real Estate connection closed")
        if self._mcp_demographics is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Demographics server...")
            await self._mcp_demographics.__aexit__(None, None, None)
            self._mcp_demographics = None
            logger.info("[SHUTDOWN] MCP Demographics connection closed")
        if self._mcp_government_data is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Government Data server...")
            await self._mcp_government_data.__aexit__(None, None, None)
            self._mcp_government_data = None
            logger.info("[SHUTDOWN] MCP Government Data connection closed")
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
    """Example usage of the Location Scout Agent."""
    async with LocationScoutAgent() as agent:
        response = await agent.run(
            "Analyze the Veveří district in Brno for coffee shop expansion"
        )
        print(f"Agent: {response}")


if __name__ == "__main__":
    asyncio.run(main())
