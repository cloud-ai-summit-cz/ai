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
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable
from uuid import uuid4

from jinja2 import Template
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
    ScratchpadSection,
    ScratchpadSnapshotData,
    ScratchpadUpdatedData,
    SSEEvent,
    SSEEventType,
    ToolCallCompletedData,
    ToolCallFailedData,
    ToolCallStartedData,
)

logger = logging.getLogger(__name__)

# === Tool Call Event Queue ===

class ToolCallEventQueue:
    """Thread-safe queue for tool call events during streaming.
    
    Middleware pushes events here; the streaming loop consumes them.
    Events include detailed input/output data for SSE streaming.
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


# Scratchpad tool names for tracking updates
SCRATCHPAD_WRITE_TOOLS = {"write_section", "append_to_section"}
SCRATCHPAD_READ_TOOLS = {"read_section", "list_sections"}
SCRATCHPAD_QUESTION_TOOLS = {"add_question", "get_pending_questions", "get_answered_questions", "submit_answers"}


def _serialize_tool_output(output: Any) -> Any:
    """Convert tool output to a JSON-serializable format.
    
    Handles various output types from agent_framework including:
    - TextContent objects
    - Pydantic models
    - Lists/tuples of mixed types
    - Dicts with non-serializable values
    
    Args:
        output: The raw output from a tool call.
        
    Returns:
        JSON-serializable representation of the output.
    """
    if output is None:
        return None
    
    # Handle TextContent from agent_framework (has .text attribute)
    if hasattr(output, "text") and hasattr(output, "type"):
        return {"type": getattr(output, "type", "text"), "text": output.text}
    
    # Handle Pydantic models
    if hasattr(output, "model_dump"):
        return output.model_dump()
    
    # Handle lists/tuples - recursively serialize each item
    if isinstance(output, (list, tuple)):
        return [_serialize_tool_output(item) for item in output]
    
    # Handle dicts - recursively serialize values
    if isinstance(output, dict):
        return {k: _serialize_tool_output(v) for k, v in output.items()}
    
    # Handle primitive types that are already serializable
    if isinstance(output, (str, int, float, bool)):
        return output
    
    # Fallback: convert to string representation
    return str(output)


def create_tool_call_middleware(
    event_queue: ToolCallEventQueue,
    call_counts: dict[str, int],
    agent_name: str = "research-orchestrator",
) -> Callable[[FunctionInvocationContext, Callable[[FunctionInvocationContext], Awaitable[None]]], Awaitable[None]]:
    """Create middleware that intercepts tool calls and pushes detailed events to the queue.
    
    This middleware wraps every function/tool call made by the agent, capturing:
    - Full input arguments (for SSE streaming)
    - Full output results (for SSE streaming)
    - Execution timing
    - Scratchpad-specific events for collaborative workspace tracking
    
    Args:
        event_queue: Queue to push tool call events to.
        call_counts: Shared dict to track call counts per tool.
        agent_name: Name of the agent making the calls.
        
    Returns:
        Middleware function for the agent.
    """
    async def tool_call_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """Middleware that captures detailed tool call inputs and outputs."""
        function_name = context.function.name
        call_counts[function_name] = call_counts.get(function_name, 0) + 1
        call_number = call_counts[function_name]
        tool_call_id = f"{function_name}_{call_number}_{uuid4().hex[:8]}"
        
        # Extract full arguments
        input_args: dict[str, Any] = {}
        if hasattr(context, "arguments") and context.arguments:
            input_args = dict(context.arguments)
        
        # Emit detailed tool call started event
        await event_queue.put({
            "type": "tool_started",
            "event_data": ToolCallStartedData(
                tool_name=function_name,
                tool_call_id=tool_call_id,
                agent_name=agent_name,
                input_args=input_args,
            ),
            "call_number": call_number,
            "timestamp": datetime.utcnow().isoformat(),
            "is_scratchpad_write": function_name in SCRATCHPAD_WRITE_TOOLS,
            "is_scratchpad_question": function_name in SCRATCHPAD_QUESTION_TOOLS,
        })
        
        logger.info(f"Tool call started: {function_name} (call #{call_number}) args={input_args}")
        start_time = datetime.utcnow()
        
        error_occurred = False
        error_message = ""
        error_type = ""
        
        try:
            # Execute the actual tool
            await next(context)
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            error_type = type(e).__name__
            logger.error(f"Tool call failed: {function_name} - {error_message}")
            raise
        finally:
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if error_occurred:
                # Emit tool call failed event
                await event_queue.put({
                    "type": "tool_failed",
                    "event_data": ToolCallFailedData(
                        tool_name=function_name,
                        tool_call_id=tool_call_id,
                        agent_name=agent_name,
                        error=error_message,
                        error_type=error_type,
                    ),
                    "call_number": call_number,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            else:
                # Extract full result and ensure it's JSON-serializable
                output: Any = None
                if hasattr(context, "result") and context.result is not None:
                    output = _serialize_tool_output(context.result)
                
                # Emit detailed tool call completed event
                await event_queue.put({
                    "type": "tool_completed",
                    "event_data": ToolCallCompletedData(
                        tool_name=function_name,
                        tool_call_id=tool_call_id,
                        agent_name=agent_name,
                        output=output,
                        execution_time_ms=execution_time_ms,
                    ),
                    "call_number": call_number,
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_scratchpad_write": function_name in SCRATCHPAD_WRITE_TOOLS,
                    "section_name": input_args.get("section_name") or input_args.get("name"),
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

    async def _get_scratchpad_snapshot(self) -> ScratchpadSnapshotData | None:
        """Fetch current scratchpad state for snapshot events.
        
        Returns:
            ScratchpadSnapshotData with all sections, or None if scratchpad unavailable.
        """
        if not self._mcp_scratchpad:
            return None
        
        try:
            # Find the list_sections function
            list_sections_fn = None
            for fn in self._mcp_scratchpad.functions:
                if fn.name == "list_sections":
                    list_sections_fn = fn
                    break
            
            if not list_sections_fn:
                logger.warning("list_sections tool not found in scratchpad")
                return None
            
            # Call list_sections to get all section names
            result = await list_sections_fn()
            
            # Parse result to extract section names
            sections: list[ScratchpadSection] = []
            
            # Handle list of content blocks (standard MAF tool output)
            full_text = ""
            if isinstance(result, list):
                for block in result:
                    if hasattr(block, "text"):
                        full_text += block.text
                    elif isinstance(block, dict) and "text" in block:
                        full_text += block["text"]
                    elif isinstance(block, str):
                        full_text += block
            elif isinstance(result, str):
                full_text = result
            
            if full_text:
                # Try parsing as JSON first (new format)
                try:
                    data = json.loads(full_text)
                    if isinstance(data, dict) and "sections" in data:
                        for s in data["sections"]:
                            sections.append(ScratchpadSection(
                                name=s.get("name", "unknown"),
                                content="",  # Content not fetched for performance
                            ))
                        return ScratchpadSnapshotData(
                            sections=sections,
                            total_sections=len(sections),
                        )
                except json.JSONDecodeError:
                    # Fallback to parsing markdown list (old format)
                    pass
                
                # Parse markdown list format
                lines = full_text.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("- "):
                        section_name = line[2:].strip()
                        sections.append(ScratchpadSection(
                            name=section_name,
                            content="",
                        ))
            
            return ScratchpadSnapshotData(
                sections=sections,
                total_sections=len(sections),
            )
        except Exception as e:
            logger.warning(f"Failed to get scratchpad snapshot: {e}")
            return None

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
            
            # Load and render system prompt
            prompt_template = self.settings.get_prompt("system_prompt")
            template = Template(prompt_template)
            system_prompt = template.render(
                query=session.query,
                context=session.context,
                scratchpad_enabled=self._mcp_scratchpad is not None
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
            iteration_count = 0
            scratchpad_sections_seen: set[str] = set()

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
                        event_data: ToolCallStartedData = tool_event["event_data"]
                        yield SSEEvent(
                            event_type=SSEEventType.TOOL_CALL_STARTED,
                            session_id=session_id,
                            data={
                                "tool_name": event_data.tool_name,
                                "tool_call_id": event_data.tool_call_id,
                                "agent_name": event_data.agent_name,
                                "input_args": event_data.input_args,
                                "call_number": tool_event["call_number"],
                            },
                        )
                        self._tool_call_log.append({
                            "tool": event_data.tool_name,
                            "tool_call_id": event_data.tool_call_id,
                            "started_at": tool_event["timestamp"],
                            "call_number": tool_event["call_number"],
                            "input_args": event_data.input_args,
                        })
                    
                    elif tool_event["type"] == "tool_completed":
                        event_data_completed: ToolCallCompletedData = tool_event["event_data"]
                        yield SSEEvent(
                            event_type=SSEEventType.TOOL_CALL_COMPLETED,
                            session_id=session_id,
                            data={
                                "tool_name": event_data_completed.tool_name,
                                "tool_call_id": event_data_completed.tool_call_id,
                                "agent_name": event_data_completed.agent_name,
                                "output": event_data_completed.output,
                                "execution_time_ms": event_data_completed.execution_time_ms,
                                "call_number": tool_event["call_number"],
                            },
                        )
                        
                        # If this was a scratchpad write, emit a scratchpad updated event
                        if tool_event.get("is_scratchpad_write"):
                            section_name = tool_event.get("section_name", "unknown")
                            operation = "created" if section_name not in scratchpad_sections_seen else "updated"
                            scratchpad_sections_seen.add(section_name)
                            
                            # Extract content preview from input args
                            input_args = self._tool_call_log[-1].get("input_args", {}) if self._tool_call_log else {}
                            content_preview = str(input_args.get("content", ""))[:500] if input_args.get("content") else None
                            
                            yield SSEEvent(
                                event_type=SSEEventType.SCRATCHPAD_UPDATED,
                                session_id=session_id,
                                data=ScratchpadUpdatedData(
                                    section_name=section_name,
                                    operation=operation,
                                    updated_by=event_data_completed.agent_name,
                                    content_preview=content_preview,
                                ).model_dump(),
                            )
                    
                    elif tool_event["type"] == "tool_failed":
                        event_data_failed: ToolCallFailedData = tool_event["event_data"]
                        yield SSEEvent(
                            event_type=SSEEventType.TOOL_CALL_FAILED,
                            session_id=session_id,
                            data={
                                "tool_name": event_data_failed.tool_name,
                                "tool_call_id": event_data_failed.tool_call_id,
                                "agent_name": event_data_failed.agent_name,
                                "error": event_data_failed.error,
                                "error_type": event_data_failed.error_type,
                                "call_number": tool_event["call_number"],
                            },
                        )

                # Stream text output
                if update.text:
                    accumulated_content += update.text
                    iteration_count += 1
                    yield SSEEvent(
                        event_type=SSEEventType.AGENT_PROGRESS,
                        session_id=session_id,
                        data={
                            "agent": "research-orchestrator",
                            "text": update.text,
                        },
                    )
                    
                    # Emit scratchpad snapshot periodically (every 10 iterations with content)
                    if self._mcp_scratchpad and iteration_count % 10 == 0:
                        snapshot = await self._get_scratchpad_snapshot()
                        if snapshot:
                            snapshot.iteration = iteration_count
                            snapshot.triggered_by = "iteration_checkpoint"
                            yield SSEEvent(
                                event_type=SSEEventType.SCRATCHPAD_SNAPSHOT,
                                session_id=session_id,
                                data=snapshot.model_dump(),
                            )

            # Drain any remaining events from the queue
            event_queue.close()
            while True:
                tool_event = event_queue.get_nowait()
                if tool_event is None:
                    break
                if tool_event["type"] == "tool_completed":
                    event_data_completed = tool_event["event_data"]
                    yield SSEEvent(
                        event_type=SSEEventType.TOOL_CALL_COMPLETED,
                        session_id=session_id,
                        data={
                            "tool_name": event_data_completed.tool_name,
                            "tool_call_id": event_data_completed.tool_call_id,
                            "agent_name": event_data_completed.agent_name,
                            "output": event_data_completed.output,
                            "execution_time_ms": event_data_completed.execution_time_ms,
                            "call_number": tool_event["call_number"],
                        },
                    )
                elif tool_event["type"] == "tool_failed":
                    event_data_failed = tool_event["event_data"]
                    yield SSEEvent(
                        event_type=SSEEventType.TOOL_CALL_FAILED,
                        session_id=session_id,
                        data={
                            "tool_name": event_data_failed.tool_name,
                            "tool_call_id": event_data_failed.tool_call_id,
                            "agent_name": event_data_failed.agent_name,
                            "error": event_data_failed.error,
                            "error_type": event_data_failed.error_type,
                            "call_number": tool_event["call_number"],
                        },
                    )

            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Emit final scratchpad snapshot
            if self._mcp_scratchpad:
                final_snapshot = await self._get_scratchpad_snapshot()
                if final_snapshot:
                    final_snapshot.triggered_by = "workflow_complete"
                    yield SSEEvent(
                        event_type=SSEEventType.SCRATCHPAD_SNAPSHOT,
                        session_id=session_id,
                        data=final_snapshot.model_dump(),
                    )

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
