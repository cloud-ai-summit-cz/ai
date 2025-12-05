"""Synthesizer Agent using Microsoft Agent Framework.

This module implements the Synthesizer agent using AzureOpenAIResponsesClient
from the Microsoft Agent Framework with MCP tool integration for reading
research findings from scratchpad and performing calculations for financial synthesis.
"""

import asyncio
import logging
from typing import Optional

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from config import Settings

logger = logging.getLogger(__name__)

# MCP connection timeout configuration
# Longer timeouts to handle Azure API Management and TLS handshake latency
MCP_CONNECTION_TIMEOUT = 60.0  # 60 seconds for initial connection/TLS handshake
MCP_SSE_READ_TIMEOUT = 120.0  # 120 seconds for SSE stream reads (tool execution)
MCP_REQUEST_TIMEOUT = 90  # 90 seconds for individual MCP requests


class SynthesizerAgent:
    """Synthesizer Agent powered by Microsoft Agent Framework.

    This agent specializes in compiling comprehensive expansion research reports
    by reading findings from other specialist agents via the MCP Scratchpad and
    synthesizing them into strategic recommendations with supporting calculations.
    Uses MCP Scratchpad for reading research findings and writing synthesis,
    and MCP Calculator for financial calculations in the final report.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Initialize the Synthesizer Agent.

        Args:
            settings: Configuration settings. If None, loads from environment.
            session_id: Optional session ID for session-scoped MCP tools.
                       When provided, enables collaboration via MCP Scratchpad.
        """
        self._settings = settings or Settings()
        self._session_id = session_id
        self._agent: ChatAgent | None = None
        self._mcp_scratchpad: MCPStreamableHTTPTool | None = None
        self._mcp_calculator: MCPStreamableHTTPTool | None = None

    @property
    def system_prompt(self) -> str:
        """Load the system prompt from file."""
        return self._settings.get_system_prompt()

    async def initialize(self) -> None:
        """Initialize the agent with Azure OpenAI connection and MCP tools."""
        if self._agent is not None:
            return

        logger.info("=" * 60)
        logger.info("[INIT] Initializing Synthesizer Agent")
        logger.info(f"[INIT] Azure OpenAI Endpoint: {self._settings.azure_openai_endpoint}")
        logger.info(f"[INIT] Model: {self._settings.model_deployment_name}")
        if self._session_id:
            logger.info(f"[INIT] Session ID: {self._session_id}")
        
        # List to collect MCP tools
        mcp_tools = []
        
        # Create MCP Scratchpad tool with session scope (REQUIRED for synthesizer)
        if self._session_id:
            logger.info(f"[MCP INIT] Connecting to MCP Scratchpad server...")
            logger.info(f"[MCP INIT] URL: {self._settings.mcp_scratchpad_url}")
            logger.info(f"[MCP INIT] Session ID: {self._session_id}")
            
            # Headers for session-scoped access
            scratchpad_headers = {
                "Authorization": f"Bearer {self._settings.mcp_scratchpad_api_key}",
                "X-Session-ID": self._session_id,
                "X-Caller-Agent": "synthesizer",
            }
            
            self._mcp_scratchpad = MCPStreamableHTTPTool(
                name="scratchpad",
                url=self._settings.mcp_scratchpad_url,
                description="Shared scratchpad for reading research findings from other agents (market_analysis, competitor_landscape, location_strategy, financial_outlook) and writing synthesis (executive_summary, recommendation, risk_assessment).",
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
            logger.warning("[MCP INIT] No session ID - scratchpad tool not enabled (synthesizer needs this!)")

        # Create MCP Calculator tool (for financial calculations in synthesis)
        logger.info(f"[MCP INIT] Connecting to MCP Calculator server...")
        logger.info(f"[MCP INIT] URL: {self._settings.mcp_calculator_url}")
        self._mcp_calculator = MCPStreamableHTTPTool(
            name="calculator",
            url=self._settings.mcp_calculator_url,
            description="Financial calculator for ROI, NPV, break-even analysis, and other calculations needed for synthesis",
            headers={"Authorization": f"Bearer {self._settings.mcp_calculator_api_key}"},
            timeout=MCP_CONNECTION_TIMEOUT,
            sse_read_timeout=MCP_SSE_READ_TIMEOUT,
            request_timeout=MCP_REQUEST_TIMEOUT,
        )
        await self._mcp_calculator.__aenter__()
        if self._mcp_calculator.functions:
            tool_names = [f.name for f in self._mcp_calculator.functions]
            logger.info(f"[MCP INIT] Calculator connection successful! {len(tool_names)} tools available:")
            for name in tool_names:
                logger.info(f"[MCP INIT]   - {name}")
        else:
            logger.warning("[MCP INIT] Calculator connected but no tools were loaded!")
        mcp_tools.append(self._mcp_calculator)

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
        if self._mcp_calculator is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Calculator server...")
            await self._mcp_calculator.__aexit__(None, None, None)
            self._mcp_calculator = None
            logger.info("[SHUTDOWN] MCP Calculator connection closed")
        if self._mcp_scratchpad is not None:
            logger.info("[SHUTDOWN] Disconnecting from MCP Scratchpad server...")
            await self._mcp_scratchpad.__aexit__(None, None, None)
            self._mcp_scratchpad = None
            logger.info("[SHUTDOWN] MCP Scratchpad connection closed")
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
    """Example usage of the Synthesizer Agent."""
    async with SynthesizerAgent() as agent:
        response = await agent.run(
            "Synthesize the research findings into a comprehensive expansion report"
        )
        print(f"Agent: {response}")


if __name__ == "__main__":
    asyncio.run(main())
