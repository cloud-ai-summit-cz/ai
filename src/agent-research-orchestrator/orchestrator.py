"""Agent orchestration using Microsoft Agent Framework.

This module provides the core orchestration logic for coordinating
multiple Foundry agents to perform research tasks using the
Microsoft Agent Framework (MAF).

Architecture: Dynamic Agent-as-Tool Pattern
- Main orchestrator agent has full autonomy to decide which agents to call
- Specialist agents (market-analyst, competitor-analyst, synthesizer) are
  exposed as tools that the orchestrator can invoke dynamically
- The orchestrator can call agents multiple times, in any order, based on
  its reasoning about the research query
- MCP Scratchpad provides shared workspace for inter-agent collaboration

Uses middleware to intercept tool calls for real-time SSE streaming.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable
from uuid import uuid4

from agent_framework import ChatAgent, FunctionInvocationContext, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential

from config import (
    Settings,
    get_settings,
    MARKET_ANALYST_AGENT_NAME,
    COMPETITOR_ANALYST_AGENT_NAME,
    SYNTHESIZER_AGENT_NAME,
)
from models import (
    AgentResult,
    AgentType,
    ResearchSession,
    ResearchSessionStatus,
    SSEEvent,
    SSEEventType,
)

logger = logging.getLogger(__name__)

# Orchestrator system prompt for dynamic agent coordination
ORCHESTRATOR_SYSTEM_PROMPT = """You are a Research Orchestrator agent that coordinates multi-agent research workflows.

You have access to specialist agents as tools:
1. **market_analysis** - Analyzes market opportunities, trends, customer segments, and market sizing
2. **competitor_analysis** - Analyzes competitive landscape, competitor strengths/weaknesses, market positioning
3. **synthesize_findings** - Combines research insights into cohesive, actionable recommendations

You also have access to a shared scratchpad for collaboration:
- **write_section** - Store findings in named sections (e.g., 'market_findings', 'competitor_analysis')
- **read_section** - Read content from a named section
- **list_sections** - List all available sections
- **add_question** - Queue questions for human review if you need clarification
- **get_answered_questions** - Check if humans have answered your questions

Your role is to:
- Understand the user's research query deeply
- Call the appropriate specialist agents to gather comprehensive insights
- Store important findings in the scratchpad for reference and synthesis
- You may call each agent MULTIPLE TIMES if needed to explore different aspects
- You may call agents in any order based on your reasoning
- After gathering sufficient information, call synthesize_findings to create the final report

Guidelines:
- Start by breaking down the query into key research areas
- For complex queries, gather both market AND competitor insights before synthesizing
- Use the scratchpad to store key findings as you go - this helps with synthesis
- If initial results raise new questions, call agents again to dig deeper
- If you need human input, use add_question to queue questions
- Always end by calling synthesize_findings with all the gathered information
- Be thorough - it's better to gather more insights than to miss important aspects

Remember: You have FULL AUTONOMY to decide how to approach the research. Use your judgment."""


# Orchestrator system prompt when scratchpad is not available
ORCHESTRATOR_SYSTEM_PROMPT_NO_SCRATCHPAD = """You are a Research Orchestrator agent that coordinates multi-agent research workflows.

You have access to specialist agents as tools:
1. **market_analysis** - Analyzes market opportunities, trends, customer segments, and market sizing
2. **competitor_analysis** - Analyzes competitive landscape, competitor strengths/weaknesses, market positioning
3. **synthesize_findings** - Combines research insights into cohesive, actionable recommendations

Your role is to:
- Understand the user's research query deeply
- Call the appropriate specialist agents to gather comprehensive insights
- You may call each agent MULTIPLE TIMES if needed to explore different aspects
- You may call agents in any order based on your reasoning
- After gathering sufficient information, call synthesize_findings to create the final report

Guidelines:
- Start by breaking down the query into key research areas
- For complex queries, gather both market AND competitor insights before synthesizing
- If initial results raise new questions, call agents again to dig deeper
- Always end by calling synthesize_findings with all the gathered information
- Be thorough - it's better to gather more insights than to miss important aspects

Remember: You have FULL AUTONOMY to decide how to approach the research. Use your judgment."""


# === Tool Call Event Queue ===

class ToolCallEventQueue:
    """Thread-safe queue for tool call events during streaming.
    
    Middleware pushes events here; the streaming loop consumes them.
    """
    
    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._closed = False
    
    async def put(self, event: dict[str, Any]) -> None:
        """Add a tool call event to the queue."""
        if not self._closed:
            await self._queue.put(event)
    
    def get_nowait(self) -> dict[str, Any] | None:
        """Get an event without waiting. Returns None if empty."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
    
    def close(self) -> None:
        """Mark the queue as closed."""
        self._closed = True


def create_tool_call_middleware(
    event_queue: ToolCallEventQueue,
    call_counts: dict[str, int],
) -> Callable[[FunctionInvocationContext, Callable[[FunctionInvocationContext], Awaitable[None]]], Awaitable[None]]:
    """Create middleware that intercepts tool calls and pushes events to the queue.
    
    This middleware wraps every function/tool call made by the agent, allowing us
    to capture tool invocations in real-time for SSE streaming.
    
    Args:
        event_queue: Queue to push tool call events to.
        call_counts: Shared dict to track call counts per tool.
        
    Returns:
        Middleware function for the agent.
    """
    async def tool_call_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """Middleware that logs tool calls and results."""
        function_name = context.function.name
        call_counts[function_name] = call_counts.get(function_name, 0) + 1
        call_number = call_counts[function_name]
        
        # Get arguments if available
        args = {}
        if hasattr(context, "arguments"):
            args = context.arguments or {}
        
        # Emit tool call started event
        await event_queue.put({
            "type": "tool_started",
            "tool": function_name,
            "call_number": call_number,
            "timestamp": datetime.utcnow().isoformat(),
            "args_preview": str(args)[:200] if args else None,
        })
        
        logger.info(f"Tool call started: {function_name} (call #{call_number})")
        start_time = datetime.utcnow()
        
        # Execute the actual tool
        await next(context)
        
        end_time = datetime.utcnow()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Get result preview if available
        result_preview = None
        if hasattr(context, "result") and context.result:
            result_str = str(context.result)
            result_preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
        
        # Emit tool call completed event
        await event_queue.put({
            "type": "tool_completed",
            "tool": function_name,
            "call_number": call_number,
            "execution_time_ms": execution_time_ms,
            "result_preview": result_preview,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"Tool call completed: {function_name} in {execution_time_ms}ms")
    
    return tool_call_middleware


class AgentOrchestrator:
    """Orchestrates multi-agent research workflows using MAF.

    This orchestrator uses the dynamic agent-as-tool pattern where:
    - A main orchestrator agent (backed by Azure OpenAI) has full autonomy
    - Specialist Foundry agents are exposed as callable tools via .as_tool()
    - MCP Scratchpad provides shared workspace for inter-agent collaboration
    - The orchestrator decides dynamically which agents to call and how often

    Specialist agents:
    1. market-analyst: Analyzes market opportunities and trends
    2. competitor-analyst: Analyzes competitive landscape
    3. synthesizer: Combines insights into actionable recommendations

    MCP Scratchpad tools:
    - write_section, read_section, list_sections: Document collaboration
    - add_question, get_answered_questions: Human-in-the-loop
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the orchestrator.

        Args:
            settings: Application settings. If None, loads from environment.
        """
        self.settings = settings or get_settings()
        self._sessions: dict[str, ResearchSession] = {}
        self._credential: DefaultAzureCredential | None = None
        self._tool_call_log: list[dict[str, Any]] = []
        self._mcp_scratchpad: MCPStreamableHTTPTool | None = None

    async def __aenter__(self) -> "AgentOrchestrator":
        """Async context manager entry."""
        self._credential = DefaultAzureCredential()
        
        # Initialize MCP Scratchpad if configured
        if self.settings.mcp_scratchpad_enabled:
            logger.info(f"Connecting to MCP Scratchpad at {self.settings.mcp_scratchpad_url}")
            self._mcp_scratchpad = MCPStreamableHTTPTool(
                name="scratchpad",
                url=self.settings.mcp_scratchpad_url,
                headers={"Authorization": f"Bearer {self.settings.mcp_scratchpad_api_key}"},
                description="Shared workspace for storing research findings and collaboration between agents",
            )
            await self._mcp_scratchpad.__aenter__()
            logger.info(f"MCP Scratchpad connected with {len(self._mcp_scratchpad.functions)} tools")
        else:
            logger.info("MCP Scratchpad not configured, running without shared workspace")
        
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # Clean up MCP Scratchpad
        if self._mcp_scratchpad:
            await self._mcp_scratchpad.__aexit__(exc_type, exc_val, exc_tb)
            self._mcp_scratchpad = None
        
        if self._credential:
            await self._credential.close()

    def _ensure_credential(self) -> DefaultAzureCredential:
        """Ensure credential is initialized."""
        if self._credential is None:
            raise RuntimeError(
                "Orchestrator not initialized. Use 'async with AgentOrchestrator() as orch:'"
            )
        return self._credential

    def _create_foundry_agent(
        self,
        agent_name: str,
        description: str = "",
    ) -> ChatAgent:
        """Create a ChatAgent wrapper for a Foundry agent.

        Args:
            agent_name: Name of the agent in Foundry (used as identifier in new API).
            description: Description of what this agent does (for tool conversion).

        Returns:
            Configured ChatAgent.
        """
        credential = self._ensure_credential()

        client = AzureAIAgentClient(
            project_endpoint=self.settings.azure_ai_foundry_endpoint,
            model_deployment_name=self.settings.model_deployment_name,
            agent_name=agent_name,
            async_credential=credential,
            should_cleanup_agent=False,
        )

        return ChatAgent(
            chat_client=client,
            name=agent_name,
            description=description,
            instructions="",  # Use agent's existing instructions
        )

    def _create_orchestrator_client(self) -> AzureAIAgentClient:
        """Create the chat client for the main orchestrator agent.

        The orchestrator uses AzureAIAgentClient which supports tool calling,
        allowing it to dynamically invoke specialist agents.

        Returns:
            Configured AzureAIAgentClient.
        """
        credential = self._ensure_credential()

        return AzureAIAgentClient(
            project_endpoint=self.settings.azure_ai_foundry_endpoint,
            model_deployment_name=self.settings.model_deployment_name,
            async_credential=credential,
        )

    # === Session Management ===

    def create_session(
        self, query: str, context: dict[str, Any] | None = None
    ) -> ResearchSession:
        """Create a new research session.

        Args:
            query: The research query to investigate.
            context: Optional additional context for agents.

        Returns:
            The created session.
        """
        session_id = str(uuid4())
        session = ResearchSession(
            session_id=session_id,
            query=query,
            status=ResearchSessionStatus.PENDING,
        )
        self._sessions[session_id] = session
        logger.info(f"Created session {session_id} for query: {query[:50]}...")
        return session

    def get_session(self, session_id: str) -> ResearchSession | None:
        """Get a session by ID.

        Args:
            session_id: The session ID to look up.

        Returns:
            The session if found, None otherwise.
        """
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[ResearchSession]:
        """List all sessions.

        Returns:
            List of all sessions.
        """
        return list(self._sessions.values())

    # === Workflow Execution ===

    async def run_research_workflow(
        self,
        session_id: str,
    ) -> AsyncGenerator[SSEEvent, None]:
        """Run the research workflow with dynamic agent-as-tool orchestration.

        This method creates a main orchestrator agent that has specialist agents
        as tools. The orchestrator autonomously decides:
        - Which agents to call
        - In what order
        - How many times to call each agent
        - When to synthesize the final report

        Uses middleware to intercept tool calls in real-time for SSE streaming.

        Streams detailed events including:
        - Agent invocations (who is being called)
        - Streaming text chunks (what agents are saying)
        - Tool calls (orchestrator decisions)
        - Agent completions (who finished)

        Args:
            session_id: The session ID to execute.

        Yields:
            SSE events for workflow progress.

        Raises:
            ValueError: If session not found.
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.status = ResearchSessionStatus.RUNNING
        session.started_at = datetime.utcnow()
        self._tool_call_log = []

        yield SSEEvent(
            event_type=SSEEventType.SESSION_STARTED,
            session_id=session_id,
            data={
                "query": session.query,
                "mode": "dynamic_orchestration",
            },
        )

        try:
            # Create specialist agents
            market_agent = self._create_foundry_agent(
                agent_name=MARKET_ANALYST_AGENT_NAME,
                description="Analyzes market opportunities, trends, customer segments, TAM/SAM/SOM, and market dynamics.",
            )
            competitor_agent = self._create_foundry_agent(
                agent_name=COMPETITOR_ANALYST_AGENT_NAME,
                description="Analyzes competitive landscape, competitor strengths and weaknesses, market positioning, and competitive threats.",
            )
            synthesizer_agent = self._create_foundry_agent(
                agent_name=SYNTHESIZER_AGENT_NAME,
                description="Synthesizes research findings into cohesive reports with actionable recommendations.",
            )

            # Convert specialist agents to tools
            # The .as_tool() method converts a ChatAgent into a callable function tool
            market_tool = market_agent.as_tool(
                name="market_analysis",
                description="Call this tool to analyze market opportunities, trends, customer segments, and market sizing for the research query.",
                arg_name="query",
                arg_description="The specific market analysis question or aspect to investigate",
            )
            competitor_tool = competitor_agent.as_tool(
                name="competitor_analysis",
                description="Call this tool to analyze competitive landscape, competitor strengths/weaknesses, and market positioning.",
                arg_name="query",
                arg_description="The specific competitor analysis question or aspect to investigate",
            )
            synthesizer_tool = synthesizer_agent.as_tool(
                name="synthesize_findings",
                description="Call this tool AFTER gathering market and competitor insights to create a final synthesized report with recommendations.",
                arg_name="context",
                arg_description="All the gathered research findings and insights to synthesize into a final report",
            )

            yield SSEEvent(
                event_type=SSEEventType.AGENT_STARTED,
                session_id=session_id,
                data={
                    "phase": "orchestration",
                    "description": "Orchestrator starting dynamic research workflow",
                    "available_tools": ["market_analysis", "competitor_analysis", "synthesize_findings"],
                    "scratchpad_enabled": self._mcp_scratchpad is not None,
                    "scratchpad_tools": [f.name for f in self._mcp_scratchpad.functions] if self._mcp_scratchpad else [],
                },
            )

            # Create event queue and middleware for tool call interception
            event_queue = ToolCallEventQueue()
            agent_call_count: dict[str, int] = {}
            tool_middleware = create_tool_call_middleware(event_queue, agent_call_count)

            # Build the tools list - agent tools + MCP scratchpad (if available)
            tools_list: list[Any] = [market_tool, competitor_tool, synthesizer_tool]
            
            # Add MCP Scratchpad if configured
            if self._mcp_scratchpad:
                tools_list.append(self._mcp_scratchpad)
                logger.info("Added MCP Scratchpad tools to orchestrator")
            
            # Select appropriate system prompt
            system_prompt = (
                ORCHESTRATOR_SYSTEM_PROMPT 
                if self._mcp_scratchpad 
                else ORCHESTRATOR_SYSTEM_PROMPT_NO_SCRATCHPAD
            )

            # Create the main orchestrator agent with specialist agents as tools
            chat_client = self._create_orchestrator_client()
            orchestrator_agent = ChatAgent(
                chat_client=chat_client,
                name="research-orchestrator",
                instructions=system_prompt,
                tools=tools_list,
            )

            # Run the orchestrator with streaming
            start_time = datetime.utcnow()
            orchestrator_thread = orchestrator_agent.get_new_thread()
            accumulated_content = ""

            # Stream the orchestrator's execution with middleware for tool call interception
            async for update in orchestrator_agent.run_stream(
                f"Please conduct comprehensive research on: {session.query}",
                thread=orchestrator_thread,
                middleware=[tool_middleware],
            ):
                # Check for queued tool call events from middleware
                while True:
                    tool_event = event_queue.get_nowait()
                    if tool_event is None:
                        break
                    
                    if tool_event["type"] == "tool_started":
                        yield SSEEvent(
                            event_type=SSEEventType.AGENT_THINKING,
                            session_id=session_id,
                            data={
                                "orchestrator_action": "calling_tool",
                                "tool": tool_event["tool"],
                                "call_number": tool_event["call_number"],
                                "args_preview": tool_event.get("args_preview"),
                            },
                        )
                        self._tool_call_log.append({
                            "tool": tool_event["tool"],
                            "started_at": tool_event["timestamp"],
                            "call_number": tool_event["call_number"],
                        })
                    
                    elif tool_event["type"] == "tool_completed":
                        yield SSEEvent(
                            event_type=SSEEventType.AGENT_COMPLETED,
                            session_id=session_id,
                            data={
                                "tool": tool_event["tool"],
                                "call_number": tool_event["call_number"],
                                "execution_time_ms": tool_event["execution_time_ms"],
                                "result_preview": tool_event.get("result_preview"),
                            },
                        )

                # Stream text output
                if update.text:
                    accumulated_content += update.text
                    yield SSEEvent(
                        event_type=SSEEventType.AGENT_PROGRESS,
                        session_id=session_id,
                        data={
                            "agent": "research-orchestrator",
                            "text": update.text,
                        },
                    )

            # Drain any remaining events from the queue
            event_queue.close()
            while True:
                tool_event = event_queue.get_nowait()
                if tool_event is None:
                    break
                if tool_event["type"] == "tool_completed":
                    yield SSEEvent(
                        event_type=SSEEventType.AGENT_COMPLETED,
                        session_id=session_id,
                        data={
                            "tool": tool_event["tool"],
                            "call_number": tool_event["call_number"],
                            "execution_time_ms": tool_event["execution_time_ms"],
                        },
                    )

            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Record the orchestrator's result
            session.agent_results.append(
                AgentResult(
                    agent_type=AgentType.SYNTHESIZER,  # Final output is the synthesis
                    agent_name="research-orchestrator",
                    content=accumulated_content,
                    execution_time_ms=execution_time_ms,
                    timestamp=end_time,
                    metadata={
                        "tool_calls": self._tool_call_log,
                        "agent_call_counts": agent_call_count,
                    },
                )
            )
            session.final_synthesis = accumulated_content

            yield SSEEvent(
                event_type=SSEEventType.SYNTHESIS_COMPLETED,
                session_id=session_id,
                data={
                    "agent": "research-orchestrator",
                    "execution_time_ms": execution_time_ms,
                    "tool_calls_made": self._tool_call_log,
                    "agent_call_counts": agent_call_count,
                },
            )

            # Workflow complete
            session.status = ResearchSessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()

            yield SSEEvent(
                event_type=SSEEventType.WORKFLOW_COMPLETED,
                session_id=session_id,
                data={
                    "total_tool_calls": len(self._tool_call_log),
                    "agent_call_counts": agent_call_count,
                    "total_time_ms": int(
                        (session.completed_at - session.started_at).total_seconds() * 1000
                    ),
                    "synthesis": accumulated_content,
                },
            )

        except Exception as e:
            session.status = ResearchSessionStatus.FAILED
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            logger.exception(f"Workflow failed for session {session_id}")

            yield SSEEvent(
                event_type=SSEEventType.WORKFLOW_FAILED,
                session_id=session_id,
                data={
                    "error": str(e),
                    "tool_calls_before_failure": self._tool_call_log,
                },
            )

    # === Health Check ===

    async def check_health(self) -> dict[str, Any]:
        """Check orchestrator health.

        Returns:
            Health status dictionary.
        """
        health = {
            "status": "ok",
            "foundry_endpoint": self.settings.azure_ai_foundry_endpoint,
            "model_deployment": self.settings.model_deployment_name,
            "orchestration_mode": "dynamic_agent_as_tool",
            "mcp_scratchpad": {
                "enabled": self.settings.mcp_scratchpad_enabled,
                "connected": self._mcp_scratchpad is not None,
                "url": self.settings.mcp_scratchpad_url if self.settings.mcp_scratchpad_enabled else None,
                "tools_count": len(self._mcp_scratchpad.functions) if self._mcp_scratchpad else 0,
            },
        }
        return health
