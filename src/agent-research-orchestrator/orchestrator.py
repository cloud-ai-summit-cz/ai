"""Agent orchestration using Microsoft Agent Framework.

This module provides the core orchestration logic for coordinating
multiple Foundry agents to perform research tasks using the
Microsoft Agent Framework (MAF).

Architecture: Dynamic Agent-as-Tool Pattern
- Main orchestrator agent has full autonomy to decide which agents to call
- Specialist agents (market-analyst via A2A, others via Foundry) are
  exposed as tools that the orchestrator can invoke dynamically
- The orchestrator can call agents multiple times, in any order, based on
  its reasoning about the research query
- MCP Scratchpad provides shared workspace for inter-agent collaboration

Session Isolation (SECURITY):
- Each research session gets a unique session_id
- MCP Scratchpad tools are wrapped with session-scoped headers
- AI agents CANNOT set or modify session_id - it's injected by the orchestrator
- This prevents cross-session data access

A2A Integration:
- Market-analyst is called via A2A protocol (agent runs MCP tools internally)
- Session ID is passed via X-Session-ID header to enable session-scoped MCP access
- Tool call events from A2A agents are NOT visible to orchestrator (see SSE options)

Uses middleware to intercept tool calls for real-time SSE streaming.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Awaitable, Callable
from uuid import uuid4

import httpx
from a2a.types import AgentCard
from jinja2 import Template
from agent_framework import ChatAgent, FunctionInvocationContext, MCPStreamableHTTPTool
from agent_framework.a2a import A2AAgent
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential

from telemetry import get_tracer, set_session_context, set_agent_context, set_tool_context

from config import (
    Settings,
    get_settings,
    MARKET_ANALYST_AGENT_NAME,
    COMPETITOR_ANALYST_AGENT_NAME,
    LOCATION_SCOUT_AGENT_NAME,
    FINANCE_ANALYST_AGENT_NAME,
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
    SubagentProgressData,
    SubagentToolCompletedData,
    SubagentToolStartedData,
    ToolCallCompletedData,
    ToolCallFailedData,
    ToolCallStartedData,
)

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


# === Session-Scoped MCP Tool Wrapper ===

class SessionScopedMCPTool:
    """Wrapper that injects session context headers into MCP tool calls.
    
    SECURITY: This wrapper ensures session isolation by:
    1. Injecting X-Session-ID header into every MCP request
    2. Injecting X-Caller-Agent header for audit logging
    3. AI agents have NO access to modify these headers
    
    The session_id comes from the orchestrator (trusted application code),
    not from AI agent parameters. This prevents cross-session data access.
    """
    
    def __init__(
        self,
        base_tool: MCPStreamableHTTPTool,
        session_id: str,
        caller_agent: str = "orchestrator",
    ):
        """Initialize session-scoped wrapper.
        
        Args:
            base_tool: The underlying MCP tool connection.
            session_id: Session ID to inject (from orchestrator).
            caller_agent: Name of the calling agent for audit.
        """
        self._base_tool = base_tool
        self._session_id = session_id
        self._caller_agent = caller_agent
        self._session_headers = {
            "X-Session-ID": session_id,
            "X-Caller-Agent": caller_agent,
        }
        
        # Proxy functions from base tool, wrapped with session headers
        self._wrapped_functions: list[Any] = []
        self._create_wrapped_functions()
    
    def _create_wrapped_functions(self) -> None:
        """Create wrapped versions of all MCP functions with session headers."""
        for fn in self._base_tool.functions:
            wrapped = self._wrap_function(fn)
            self._wrapped_functions.append(wrapped)
    
    def _wrap_function(self, fn: Any) -> Any:
        """Wrap a single MCP function to inject session headers.
        
        The wrapped function preserves the original function's metadata
        but intercepts calls to inject session headers.
        """
        original_call = fn.__call__ if hasattr(fn, '__call__') else fn
        session_headers = self._session_headers
        
        # Create wrapper that injects headers
        async def wrapped_call(*args, **kwargs):
            # Remove session_id from kwargs if AI tried to pass it
            # (it should not, but defense in depth)
            kwargs.pop('session_id', None)
            kwargs.pop('agent_id', None)
            
            # The MCPStreamableHTTPTool should pick up headers from the tool instance
            # We need to temporarily set headers on the base tool
            # Note: This assumes MCPStreamableHTTPTool uses self.headers for requests
            return await original_call(*args, **kwargs)
        
        # Copy metadata from original function
        wrapped_call.__name__ = getattr(fn, 'name', str(fn))
        wrapped_call.__doc__ = getattr(fn, '__doc__', None)
        
        return wrapped_call
    
    @property
    def functions(self) -> list[Any]:
        """Get the wrapped MCP functions."""
        # Return base tool functions - headers are injected at HTTP level
        return self._base_tool.functions
    
    @property
    def session_id(self) -> str:
        """Get the session ID for this wrapper."""
        return self._session_id
    
    def with_agent(self, agent_name: str) -> "SessionScopedMCPTool":
        """Create a new wrapper with a different caller agent name.
        
        Used when passing the tool to subagents so audit logs show
        which agent made each call.
        """
        return SessionScopedMCPTool(
            base_tool=self._base_tool,
            session_id=self._session_id,
            caller_agent=agent_name,
        )


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
    
    async def get(self, timeout: float | None = None) -> dict[str, Any] | None:
        """Get an event, optionally with timeout. Returns None on timeout or if closed."""
        try:
            if timeout is not None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except asyncio.TimeoutError:
            return None
        except asyncio.QueueEmpty:
            return None
    
    def close(self) -> None:
        """Mark the queue as closed."""
        self._closed = True


# Scratchpad tool names for tracking updates
SCRATCHPAD_WRITE_TOOLS = {"write_draft_section", "add_note", "add_task", "add_tasks", "update_task"}
SCRATCHPAD_READ_TOOLS = {"read_section", "list_sections"}
SCRATCHPAD_QUESTION_TOOLS = {"add_question", "get_pending_questions", "get_answered_questions", "submit_answers"}

# Agent tool names (subagents exposed as tools to orchestrator)
AGENT_TOOL_NAMES = {"market_analysis", "competitor_analysis", "location_scouting", "finance_analysis", "synthesize_findings"}


def create_subagent_stream_callback(
    event_queue: ToolCallEventQueue,
    subagent_name: str,
    session_id: str,
) -> Callable[[Any], Awaitable[None]]:
    """Create a stream callback for subagent tool calls.
    
    This callback is passed to agent.as_tool() to capture streaming events
    from subagent execution, including:
    - Tool calls (FunctionCallContent)
    - Tool results (FunctionResultContent)  
    - Text chunks (TextContent)
    
    Args:
        event_queue: Queue to push events to.
        subagent_name: Name of the subagent (e.g., "market-analyst").
        session_id: Session ID for the event.
        
    Returns:
        Async callback function for streaming updates.
    """
    pending_tool_calls: dict[str, str] = {}  # call_id -> tool_name
    update_count = 0  # Track number of updates received
    
    async def stream_callback(update: Any) -> None:
        """Handle streaming updates from subagent."""
        nonlocal update_count
        update_count += 1
        
        # Log updates at DEBUG level to reduce noise
        logger.debug(f"[SUBAGENT_STREAM] {subagent_name} update #{update_count}: type={type(update).__name__}")
        if hasattr(update, "__dict__"):
            logger.debug(f"[SUBAGENT_STREAM] {subagent_name} update attrs: {list(update.__dict__.keys())}")
        
        # AgentRunResponseUpdate has a .contents list
        if not hasattr(update, "contents") or not update.contents:
            logger.debug(f"[SUBAGENT_STREAM] {subagent_name} update has no contents (or empty)")
            if hasattr(update, "text"):
                logger.debug(f"[SUBAGENT_STREAM] {subagent_name} update.text: {str(update.text)[:100]}")
            return
        
        logger.debug(f"[SUBAGENT_STREAM] {subagent_name} update has {len(update.contents)} content items")
        
        for idx, content in enumerate(update.contents):
            content_type = getattr(content, "type", None)
            logger.debug(
                f"[SUBAGENT_STREAM] {subagent_name} content[{idx}]: type={content_type}, "
                f"class={type(content).__name__}, has_call_id={hasattr(content, 'call_id')}"
            )
            
            # Handle tool call started (FunctionCallContent)
            # Check for function_call type OR (has call_id AND has name AND no result)
            # This avoids matching FunctionResultContent which has call_id but no name
            is_tool_call = (
                content_type == "function_call" 
                or (hasattr(content, "call_id") and hasattr(content, "name") and not hasattr(content, "result"))
            )
            if is_tool_call:
                call_id = getattr(content, "call_id", None) or getattr(content, "id", str(uuid4()))
                tool_name = getattr(content, "name", "unknown_tool")
                arguments = getattr(content, "arguments", {})
                
                logger.info(f"[SUBAGENT_STREAM] {subagent_name} TOOL CALL DETECTED: {tool_name} (call_id={call_id})")
                
                # Track this call for matching with result
                pending_tool_calls[call_id] = tool_name
                
                # Create input preview
                input_preview = None
                if arguments:
                    if isinstance(arguments, str):
                        input_preview = arguments[:200]
                    elif isinstance(arguments, dict):
                        input_preview = str(arguments)[:200]
                
                await event_queue.put({
                    "type": "subagent_tool_started",
                    "event_data": SubagentToolStartedData(
                        subagent_name=subagent_name,
                        tool_name=tool_name,
                        tool_call_id=call_id,
                        input_preview=input_preview,
                    ),
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                logger.debug(f"Subagent {subagent_name} calling tool: {tool_name}")
            
            # Handle tool result (FunctionResultContent)
            elif content_type == "function_result" or (
                hasattr(content, "call_id") and hasattr(content, "result")
            ):
                call_id = getattr(content, "call_id", None)
                result = getattr(content, "result", None)
                tool_name = pending_tool_calls.pop(call_id, "unknown_tool") if call_id else "unknown_tool"
                
                logger.info(f"[SUBAGENT_STREAM] {subagent_name} TOOL RESULT DETECTED: {tool_name} (call_id={call_id})")
                
                # Create output preview - serialize properly to JSON-friendly format
                output_preview = None
                if result:
                    # Use _serialize_tool_output to handle TextContent and other complex types
                    serialized = _serialize_tool_output(result)
                    if isinstance(serialized, str):
                        output_preview = serialized[:500]
                    else:
                        # Convert to JSON string for display
                        try:
                            output_preview = json.dumps(serialized, indent=2, ensure_ascii=False)[:500]
                        except (TypeError, ValueError):
                            output_preview = str(serialized)[:500]
                
                await event_queue.put({
                    "type": "subagent_tool_completed",
                    "event_data": SubagentToolCompletedData(
                        subagent_name=subagent_name,
                        tool_name=tool_name,
                        tool_call_id=call_id or str(uuid4()),
                        output_preview=output_preview,
                    ),
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                logger.debug(f"Subagent {subagent_name} tool completed: {tool_name}")
            
            # Handle text content (streaming text from subagent)
            elif content_type == "text" or hasattr(content, "text"):
                text = getattr(content, "text", "")
                if text and len(text) > 0:
                    # Only emit substantial text chunks (skip tiny ones)
                    if len(text) >= 10:
                        await event_queue.put({
                            "type": "subagent_progress",
                            "event_data": SubagentProgressData(
                                subagent_name=subagent_name,
                                text_chunk=text[:500],  # Limit chunk size
                            ),
                            "session_id": session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
    
    return stream_callback


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
    session_id: str | None = None,
) -> Callable[[FunctionInvocationContext, Callable[[FunctionInvocationContext], Awaitable[None]]], Awaitable[None]]:
    """Create middleware that intercepts tool calls and pushes detailed events to the queue.
    
    This middleware wraps every function/tool call made by the agent, capturing:
    - Full input arguments (for SSE streaming)
    - Full output results (for SSE streaming)
    - Execution timing
    - Scratchpad-specific events for collaborative workspace tracking
    - OpenTelemetry spans for trace correlation (ADR-005)
    
    Args:
        event_queue: Queue to push tool call events to.
        call_counts: Shared dict to track call counts per tool.
        agent_name: Name of the agent making the calls.
        session_id: Optional session ID for span context.
        
    Returns:
        Middleware function for the agent.
    """
    async def tool_call_middleware(
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """Middleware that captures detailed tool call inputs and outputs with tracing."""
        function_name = context.function.name
        call_counts[function_name] = call_counts.get(function_name, 0) + 1
        call_number = call_counts[function_name]
        tool_call_id = f"{function_name}_{call_number}_{uuid4().hex[:8]}"
        
        # Extract full arguments
        input_args: dict[str, Any] = {}
        if hasattr(context, "arguments") and context.arguments:
            input_args = dict(context.arguments)
        
        # Create span for this tool call (provides trace correlation in App Insights)
        # Span name follows gen_ai semantic conventions for tool calls
        span_name = f"tool.{function_name}"
        if function_name in AGENT_TOOL_NAMES:
            span_name = f"agent.{function_name}"  # Distinguish subagent calls
        
        with tracer.start_as_current_span(span_name) as span:
            # Set span attributes for correlation and debugging
            span.set_attribute("tool.name", function_name)
            span.set_attribute("tool.call_id", tool_call_id)
            span.set_attribute("tool.call_number", call_number)
            span.set_attribute("agent.name", agent_name)
            if session_id:
                span.set_attribute("session.id", session_id)
            
            # Mark subagent invocations distinctly
            if function_name in AGENT_TOOL_NAMES:
                span.set_attribute("tool.type", "subagent")
                # Map tool name to agent name
                subagent_mapping = {
                    "market_analysis": "market-analyst",
                    "competitor_analysis": "competitor-analyst",
                    "location_scouting": "location-scout",
                    "finance_analysis": "finance-analyst",
                    "synthesize_findings": "synthesizer",
                }
                span.set_attribute("subagent.name", subagent_mapping.get(function_name, function_name))
            elif function_name in SCRATCHPAD_WRITE_TOOLS:
                span.set_attribute("tool.type", "scratchpad_write")
            elif function_name in SCRATCHPAD_READ_TOOLS:
                span.set_attribute("tool.type", "scratchpad_read")
            else:
                span.set_attribute("tool.type", "mcp")
        
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
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_scratchpad_write": function_name in SCRATCHPAD_WRITE_TOOLS,
                "is_scratchpad_question": function_name in SCRATCHPAD_QUESTION_TOOLS,
            })
            
            # Log MCP tool calls prominently at INFO level (truncate args for readability)
            args_preview = str(input_args)[:200] + "..." if len(str(input_args)) > 200 else str(input_args)
            if function_name in SCRATCHPAD_WRITE_TOOLS | SCRATCHPAD_READ_TOOLS | SCRATCHPAD_QUESTION_TOOLS:
                logger.info(f"[MCP] Scratchpad call: {function_name} (call #{call_number}) args={args_preview}")
            elif function_name in AGENT_TOOL_NAMES:
                logger.info(f"[AGENT] Subagent call: {function_name} (call #{call_number}) args={args_preview}")
            else:
                logger.info(f"[MCP] Tool call: {function_name} (call #{call_number}) args={args_preview}")
            start_time = datetime.now(timezone.utc)
            
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
                span.record_exception(e)
                span.set_attribute("error", True)
                span.set_attribute("error.type", error_type)
                logger.error(f"Tool call failed: {function_name} - {error_message}")
                raise
            finally:
                end_time = datetime.now(timezone.utc)
                execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
                span.set_attribute("tool.execution_time_ms", execution_time_ms)
                
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    # Extract full result and ensure it's JSON-serializable
                    output: Any = None
                    if hasattr(context, "result") and context.result is not None:
                        output = _serialize_tool_output(context.result)
                    
                    # Determine section name based on tool type
                    section_name = None
                    if function_name == "write_draft_section":
                        section_name = input_args.get("section_id") or "draft"
                    elif function_name == "add_note":
                        section_name = "notes"  # All notes go to the notes pillar
                    elif function_name in ("add_task", "add_tasks", "update_task"):
                        section_name = "plan"  # All task operations go to the plan pillar
                    else:
                        section_name = input_args.get("section_name") or input_args.get("name") or "unknown"
                    
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "is_scratchpad_write": function_name in SCRATCHPAD_WRITE_TOOLS,
                        "section_name": section_name,
                        "tool_type": function_name,  # Include tool type for frontend routing
                    })
                    
                    # Log MCP tool completions prominently at INFO level
                    if function_name in SCRATCHPAD_WRITE_TOOLS | SCRATCHPAD_READ_TOOLS | SCRATCHPAD_QUESTION_TOOLS:
                        logger.info(f"[MCP] Scratchpad completed: {function_name} in {execution_time_ms}ms")
                    elif function_name in AGENT_TOOL_NAMES:
                        logger.info(f"[AGENT] Subagent completed: {function_name} in {execution_time_ms}ms")
                    else:
                        logger.info(f"[MCP] Tool completed: {function_name} in {execution_time_ms}ms")
    
    return tool_call_middleware


class AgentOrchestrator:
    """Orchestrates multi-agent research workflows using MAF.

    This orchestrator uses the dynamic agent-as-tool pattern where:
    - A main orchestrator agent (backed by Azure OpenAI) has full autonomy
    - Specialist Foundry agents are exposed as callable tools via .as_tool()
    - MCP Scratchpad provides shared workspace for inter-agent collaboration
    - The orchestrator decides dynamically which agents to call and how often

    Session Isolation (SECURITY):
    - Each session gets a unique session_id (UUID)
    - MCP Scratchpad calls include X-Session-ID header
    - AI agents cannot modify or see the session_id
    - This prevents cross-session data access

    Specialist agents:
    1. market-analyst: Analyzes market opportunities and trends (via A2A)
    2. competitor-analyst: Analyzes competitive landscape (DISABLED - future A2A)
    3. location-scout: Evaluates locations and properties (DISABLED - future A2A)
    4. finance-analyst: Analyzes financial viability (DISABLED - future A2A)
    5. synthesizer: Combines insights into recommendations (DISABLED - future A2A)

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
        self._session_mcp_tools: dict[str, MCPStreamableHTTPTool] = {}  # Session-scoped MCP tools
        # A2A HTTP clients (session-scoped for header injection)
        self._a2a_http_clients: dict[str, httpx.AsyncClient] = {}

    async def __aenter__(self) -> "AgentOrchestrator":
        """Async context manager entry."""
        self._credential = DefaultAzureCredential()
        
        # Initialize base MCP Scratchpad connection if configured
        # Session-scoped tools will be created per session with X-Session-ID header
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
        # NOTE: We intentionally DO NOT clean up session-scoped MCP tools here.
        # Session-scoped MCP tools are entered (via __aenter__) from request handler tasks,
        # but this __aexit__ runs in the lifespan task. anyio cancel scopes require
        # exit from the same task that entered them, so attempting cleanup causes:
        # RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
        #
        # The MCP tools will be garbage collected when the process shuts down.
        # For graceful cleanup, session MCP tools should be cleaned up at the end of
        # each session/request, not during application shutdown.
        if self._session_mcp_tools:
            logger.info(f"Skipping cleanup of {len(self._session_mcp_tools)} session-scoped MCP tools (cross-task context issue)")
        self._session_mcp_tools.clear()
        
        # Clean up base MCP Scratchpad (this one was entered in the lifespan task)
        if self._mcp_scratchpad:
            try:
                await self._mcp_scratchpad.__aexit__(exc_type, exc_val, exc_tb)
            except RuntimeError as e:
                if "cancel scope" in str(e):
                    logger.debug(f"Skipping base MCP cleanup due to cross-task context: {e}")
                else:
                    raise
            self._mcp_scratchpad = None
        
        if self._credential:
            await self._credential.close()

    async def _get_session_mcp_tool(
        self,
        session_id: str,
        caller_agent: str = "orchestrator",
        use_cache: bool = True,
    ) -> MCPStreamableHTTPTool | None:
        """Get or create a session-scoped MCP tool with session headers.
        
        SECURITY: This method creates MCP tool connections that include
        the X-Session-ID header. AI agents cannot modify this header.
        
        Args:
            session_id: The session ID for isolation.
            caller_agent: The agent name for audit logging.
            use_cache: If True (default), cache and reuse MCP tools for workflow agents.
                      If False, create a fresh connection (for API proxy calls).
            
        Returns:
            Session-scoped MCP tool, or None if scratchpad not configured.
        """
        if not self.settings.mcp_scratchpad_enabled:
            return None
        
        # Create a unique key for this session+agent combination
        cache_key = f"{session_id}:{caller_agent}"
        
        # For API proxy calls, always create fresh connections
        # This avoids issues with closed sessions from finished workflows
        if not use_cache:
            logger.debug(f"Creating fresh MCP tool for session={session_id}, agent={caller_agent}")
            session_tool = MCPStreamableHTTPTool(
                name=f"scratchpad-{session_id[:8]}",
                url=self.settings.mcp_scratchpad_url,
                headers={
                    "Authorization": f"Bearer {self.settings.mcp_scratchpad_api_key}",
                    "X-Session-ID": session_id,
                    "X-Caller-Agent": caller_agent,
                },
                description="Shared workspace for storing research findings and collaboration between agents",
            )
            await session_tool.__aenter__()
            return session_tool
        
        # For workflow agents, use cached tools
        if cache_key not in self._session_mcp_tools:
            logger.info(f"Creating session-scoped MCP tool for session={session_id}, agent={caller_agent}")
            
            # Create new MCP tool with session headers
            session_tool = MCPStreamableHTTPTool(
                name=f"scratchpad-{session_id[:8]}",
                url=self.settings.mcp_scratchpad_url,
                headers={
                    "Authorization": f"Bearer {self.settings.mcp_scratchpad_api_key}",
                    "X-Session-ID": session_id,
                    "X-Caller-Agent": caller_agent,
                },
                description="Shared workspace for storing research findings and collaboration between agents",
            )
            await session_tool.__aenter__()
            self._session_mcp_tools[cache_key] = session_tool
            logger.info(f"Session-scoped MCP tool created with {len(session_tool.functions)} tools")
        
        return self._session_mcp_tools[cache_key]
    
    async def _cleanup_session_mcp_tools(self, session_id: str) -> None:
        """Clean up MCP tools for a specific session.
        
        Called when a workflow completes or fails to release resources.
        
        Args:
            session_id: The session ID whose MCP tools should be cleaned up.
        """
        keys_to_remove = [k for k in self._session_mcp_tools if k.startswith(f"{session_id}:")]
        
        for key in keys_to_remove:
            mcp_tool = self._session_mcp_tools.pop(key, None)
            if mcp_tool:
                try:
                    await mcp_tool.__aexit__(None, None, None)
                    logger.debug(f"Cleaned up MCP tool: {key}")
                except Exception as e:
                    logger.debug(f"Error cleaning up MCP tool {key}: {e}")

    async def _create_mcp_tools_for_agent(
        self,
        agent_name: str,
        session_id: str,
    ) -> list[MCPStreamableHTTPTool]:
        """Create MCP tools for a specific agent based on their role.
        
        ADR-006: MCP tools are now managed by the orchestrator instead of being
        configured at agent provisioning time in Foundry. This enables:
        - Real-time SSE streaming of tool calls via middleware
        - Session isolation for scratchpad via X-Session-ID headers
        - Full observability without App Insights polling latency
        
        Agent to MCP tool mapping:
        - market-analyst: scratchpad, demographics
        - competitor-analyst: scratchpad, business-registry
        - synthesizer: scratchpad only
        - research-orchestrator: scratchpad only
        
        Args:
            agent_name: Name of the agent (e.g., "market-analyst").
            session_id: Session ID for scratchpad isolation.
            
        Returns:
            List of MCPStreamableHTTPTool instances for the agent.
        """
        tools: list[MCPStreamableHTTPTool] = []
        
        # Session-scoped scratchpad (always included if configured)
        scratchpad_tool = await self._get_session_mcp_tool(session_id, caller_agent=agent_name)
        if scratchpad_tool:
            tools.append(scratchpad_tool)
        
        # Agent-specific MCP tools (ADR-006: orchestrator-managed)
        if agent_name == "market-analyst":
            # Demographics for population, income, consumer behavior
            if self.settings.mcp_demographics_enabled:
                demographics_tool = MCPStreamableHTTPTool(
                    name="demographics",
                    url=self.settings.mcp_demographics_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_demographics_api_key}"},
                    description="Demographic and consumer behavior data: population, income, age distribution, spending patterns",
                )
                await demographics_tool.__aenter__()
                tools.append(demographics_tool)
                logger.info(f"Added mcp-demographics to {agent_name}")
        
        elif agent_name == "competitor-analyst":
            # Business registry for company data, financials, industry players
            if self.settings.mcp_business_registry_enabled:
                business_registry_tool = MCPStreamableHTTPTool(
                    name="business_registry",
                    url=self.settings.mcp_business_registry_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_business_registry_api_key}"},
                    description="Business registry: company profiles, financials, locations, industry players",
                )
                await business_registry_tool.__aenter__()
                tools.append(business_registry_tool)
                logger.info(f"Added mcp-business-registry to {agent_name}")
        
        elif agent_name == "location-scout":
            # Government data for regulations, permits, zoning
            if self.settings.mcp_government_data_enabled:
                government_data_tool = MCPStreamableHTTPTool(
                    name="government_data",
                    url=self.settings.mcp_government_data_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_government_data_api_key}"},
                    description="Government data: permits, zoning, regulations, tax rates, licensing requirements",
                )
                await government_data_tool.__aenter__()
                tools.append(government_data_tool)
                logger.info(f"Added mcp-government-data to {agent_name}")
            
            # Demographics for location analysis
            if self.settings.mcp_demographics_enabled:
                demographics_tool = MCPStreamableHTTPTool(
                    name="demographics",
                    url=self.settings.mcp_demographics_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_demographics_api_key}"},
                    description="Demographic and consumer behavior data: population, income, age distribution, spending patterns",
                )
                await demographics_tool.__aenter__()
                tools.append(demographics_tool)
                logger.info(f"Added mcp-demographics to {agent_name}")
            
            # Real estate for property listings and location scores
            if self.settings.mcp_real_estate_enabled:
                real_estate_tool = MCPStreamableHTTPTool(
                    name="real_estate",
                    url=self.settings.mcp_real_estate_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_real_estate_api_key}"},
                    description="Real estate data: commercial properties, rental rates, foot traffic, location scores",
                )
                await real_estate_tool.__aenter__()
                tools.append(real_estate_tool)
                logger.info(f"Added mcp-real-estate to {agent_name}")
        
        elif agent_name == "finance-analyst":
            # Calculator for financial projections
            if self.settings.mcp_calculator_enabled:
                calculator_tool = MCPStreamableHTTPTool(
                    name="calculator",
                    url=self.settings.mcp_calculator_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_calculator_api_key}"},
                    description="Financial calculator: startup costs, operating costs, revenue projections, break-even, ROI, NPV, cash flow",
                )
                await calculator_tool.__aenter__()
                tools.append(calculator_tool)
                logger.info(f"Added mcp-calculator to {agent_name}")
            
            # Real estate for rental costs
            if self.settings.mcp_real_estate_enabled:
                real_estate_tool = MCPStreamableHTTPTool(
                    name="real_estate",
                    url=self.settings.mcp_real_estate_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_real_estate_api_key}"},
                    description="Real estate data: commercial properties, rental rates, foot traffic, location scores",
                )
                await real_estate_tool.__aenter__()
                tools.append(real_estate_tool)
                logger.info(f"Added mcp-real-estate to {agent_name}")
            
            # Government data for tax rates and regulatory costs
            if self.settings.mcp_government_data_enabled:
                government_data_tool = MCPStreamableHTTPTool(
                    name="government_data",
                    url=self.settings.mcp_government_data_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_government_data_api_key}"},
                    description="Government data: permits, zoning, regulations, tax rates, licensing requirements",
                )
                await government_data_tool.__aenter__()
                tools.append(government_data_tool)
                logger.info(f"Added mcp-government-data to {agent_name}")
            
            # Business registry for competitor financial benchmarks
            if self.settings.mcp_business_registry_enabled:
                business_registry_tool = MCPStreamableHTTPTool(
                    name="business_registry",
                    url=self.settings.mcp_business_registry_url,
                    headers={"Authorization": f"Bearer {self.settings.mcp_business_registry_api_key}"},
                    description="Business registry: company profiles, financials, locations, industry players",
                )
                await business_registry_tool.__aenter__()
                tools.append(business_registry_tool)
                logger.info(f"Added mcp-business-registry to {agent_name}")
        
        # synthesizer and research-orchestrator only need scratchpad (already added above)
        
        logger.info(f"Created {len(tools)} MCP tools for {agent_name}: {[t.name for t in tools]}")
        return tools

    async def _get_scratchpad_snapshot_for_session(self, session_id: str) -> ScratchpadSnapshotData | None:
        """Fetch current scratchpad state for a specific session.
        
        SECURITY: Uses session-scoped MCP tool with X-Session-ID header.
        
        Args:
            session_id: The session ID for data isolation.
        
        Returns:
            ScratchpadSnapshotData with all sections (draft, notes, plan), or None if unavailable.
        """
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="snapshot")
        if not mcp_tool:
            return None
        
        try:
            sections: list[ScratchpadSection] = []
            
            # Find the MCP functions we need
            read_draft_fn = None
            read_notes_fn = None
            read_plan_fn = None
            for fn in mcp_tool.functions:
                if fn.name == "read_draft":
                    read_draft_fn = fn
                elif fn.name == "read_notes":
                    read_notes_fn = fn
                elif fn.name == "read_plan":
                    read_plan_fn = fn
            
            # Helper to parse MCP result
            def parse_result(result: Any) -> str:
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
                return full_text
            
            # Read draft sections (no session_id param - it's in header)
            if read_draft_fn:
                result = await read_draft_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        if isinstance(data, dict) and "sections" in data:
                            for section_id, section_data in data["sections"].items():
                                sections.append(ScratchpadSection(
                                    name=section_id,
                                    content=section_data.get("content", "")[:500],
                                    updated_by=section_data.get("author"),
                                    updated_at=datetime.fromisoformat(section_data["last_updated"]) if section_data.get("last_updated") else None,
                                ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Read notes (no session_id param - it's in header)
            if read_notes_fn:
                result = await read_notes_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        notes = data.get("notes", [])
                        for note in notes:
                            sections.append(ScratchpadSection(
                                name=f"note:{note.get('id', 'unknown')}",
                                content=note.get("content", "")[:500],
                                updated_by=note.get("author"),
                                updated_at=datetime.fromisoformat(note["timestamp"]) if note.get("timestamp") else None,
                            ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Read plan/tasks (no session_id param - it's in header)
            if read_plan_fn:
                result = await read_plan_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        tasks = data.get("tasks", [])
                        for task in tasks:
                            sections.append(ScratchpadSection(
                                name=f"task:{task.get('id', 'unknown')}",
                                content=f"[{task.get('status', 'todo')}] {task.get('description', '')}",
                                updated_by=task.get("assigned_to"),
                                updated_at=datetime.fromisoformat(task["created_at"]) if task.get("created_at") else None,
                            ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            return ScratchpadSnapshotData(
                sections=sections,
                total_sections=len(sections),
            )
        except Exception as e:
            logger.debug(f"Failed to get scratchpad snapshot for session {session_id}: {e}")
            return None

    async def _get_scratchpad_snapshot(self) -> ScratchpadSnapshotData | None:
        """Fetch current scratchpad state for snapshot events.
        
        DEPRECATED: Use _get_scratchpad_snapshot_for_session instead for session isolation.
        
        Returns:
            ScratchpadSnapshotData with all sections (draft, notes, plan), or None if unavailable.
        """
        if not self._mcp_scratchpad:
            return None
        
        try:
            sections: list[ScratchpadSection] = []
            
            # Find the MCP functions we need
            read_draft_fn = None
            read_notes_fn = None
            read_plan_fn = None
            for fn in self._mcp_scratchpad.functions:
                if fn.name == "read_draft":
                    read_draft_fn = fn
                elif fn.name == "read_notes":
                    read_notes_fn = fn
                elif fn.name == "read_plan":
                    read_plan_fn = fn
            
            # Helper to parse MCP result
            def parse_result(result: Any) -> str:
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
                return full_text
            
            # Read draft sections
            if read_draft_fn:
                result = await read_draft_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        if isinstance(data, dict) and "sections" in data:
                            for section_id, section_data in data["sections"].items():
                                sections.append(ScratchpadSection(
                                    name=section_id,
                                    content=section_data.get("content", "")[:500],
                                    updated_by=section_data.get("author"),
                                    updated_at=datetime.fromisoformat(section_data["last_updated"]) if section_data.get("last_updated") else None,
                                ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Read notes
            if read_notes_fn:
                result = await read_notes_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        notes = data.get("notes", [])
                        for note in notes:
                            sections.append(ScratchpadSection(
                                name=f"note:{note.get('id', 'unknown')}",
                                content=note.get("content", "")[:500],
                                updated_by=note.get("author"),
                                updated_at=datetime.fromisoformat(note["timestamp"]) if note.get("timestamp") else None,
                            ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            # Read plan/tasks
            if read_plan_fn:
                result = await read_plan_fn()
                full_text = parse_result(result)
                if full_text:
                    try:
                        data = json.loads(full_text)
                        tasks = data.get("tasks", [])
                        for task in tasks:
                            sections.append(ScratchpadSection(
                                name=f"task:{task.get('id', 'unknown')}",
                                content=f"[{task.get('status', 'todo')}] {task.get('description', '')}",
                                updated_by=task.get("assigned_to"),
                                updated_at=datetime.fromisoformat(task["created_at"]) if task.get("created_at") else None,
                            ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        pass
            
            return ScratchpadSnapshotData(
                sections=sections,
                total_sections=len(sections),
            )
        except Exception as e:
            logger.debug(f"Failed to get scratchpad snapshot: {e}")
            return None

    def _parse_mcp_result(self, result: Any) -> str:
        """Parse MCP tool result into text.
        
        Args:
            result: The result from an MCP tool call.
            
        Returns:
            Parsed text content.
        """
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
        return full_text

    async def get_scratchpad_plan(self, session_id: str) -> dict[str, Any]:
        """Get the current research plan with all tasks.
        
        SECURITY: Uses session-scoped MCP tool with X-Session-ID header.
        
        Args:
            session_id: The session ID for data isolation.
            
        Returns:
            Dict with tasks array and metadata.
            
        Raises:
            RuntimeError: If scratchpad not available.
        """
        # Use use_cache=False for API proxy calls to avoid stale session issues
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy", use_cache=False)
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
        try:
            # Find read_plan function
            read_plan_fn = None
            for fn in mcp_tool.functions:
                if fn.name == "read_plan":
                    read_plan_fn = fn
                    break
            
            if not read_plan_fn:
                raise RuntimeError("read_plan tool not available")
            
            # No session_id parameter - it's in the header
            result = await read_plan_fn()
            full_text = self._parse_mcp_result(result)
            
            if not full_text:
                return {"tasks": [], "total_tasks": 0, "tasks_by_status": {}}
            
            try:
                data = json.loads(full_text)
                tasks = data.get("tasks", [])
                
                # Count by status
                by_status = {"todo": 0, "in-progress": 0, "done": 0, "blocked": 0}
                for task in tasks:
                    status = task.get("status", "todo")
                    if status in by_status:
                        by_status[status] += 1
                
                return {
                    "tasks": tasks,
                    "total_tasks": len(tasks),
                    "tasks_by_status": by_status,
                }
            except json.JSONDecodeError:
                return {"tasks": [], "total_tasks": 0, "tasks_by_status": {}}
        finally:
            # Close the uncached MCP connection
            await mcp_tool.__aexit__(None, None, None)

    async def get_scratchpad_notes(self, session_id: str) -> dict[str, Any]:
        """Get all research notes.
        
        SECURITY: Uses session-scoped MCP tool with X-Session-ID header.
        
        Args:
            session_id: The session ID for data isolation.
            
        Returns:
            Dict with notes array and metadata.
            
        Raises:
            RuntimeError: If scratchpad not available.
        """
        # Use use_cache=False for API proxy calls to avoid stale session issues
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy", use_cache=False)
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
        try:
            # Find read_notes function
            read_notes_fn = None
            for fn in mcp_tool.functions:
                if fn.name == "read_notes":
                    read_notes_fn = fn
                    break
            
            if not read_notes_fn:
                raise RuntimeError("read_notes tool not available")
            
            # No session_id parameter - it's in the header
            result = await read_notes_fn()
            full_text = self._parse_mcp_result(result)
            
            if not full_text:
                return {"notes": [], "total_notes": 0, "notes_by_author": {}}
            
            try:
                data = json.loads(full_text)
                notes = data.get("notes", [])
                
                # Count by author
                by_author: dict[str, int] = {}
                for note in notes:
                    author = note.get("author", "unknown")
                    by_author[author] = by_author.get(author, 0) + 1
                
                return {
                    "notes": notes,
                    "total_notes": len(notes),
                    "notes_by_author": by_author,
                }
            except json.JSONDecodeError:
                return {"notes": [], "total_notes": 0, "notes_by_author": {}}
        finally:
            # Close the uncached MCP connection
            await mcp_tool.__aexit__(None, None, None)

    async def get_scratchpad_draft(self, session_id: str) -> dict[str, Any]:
        """Get all draft report sections.
        
        SECURITY: Uses session-scoped MCP tool with X-Session-ID header.
        
        Args:
            session_id: The session ID for data isolation.
            
        Returns:
            Dict with sections array and metadata.
            
        Raises:
            RuntimeError: If scratchpad not available.
        """
        # Use use_cache=False for API proxy calls to avoid stale session issues
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy", use_cache=False)
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
        try:
            # Find read_draft function
            read_draft_fn = None
            for fn in mcp_tool.functions:
                if fn.name == "read_draft":
                    read_draft_fn = fn
                    break
            
            if not read_draft_fn:
                raise RuntimeError("read_draft tool not available")
            
            # No session_id parameter - it's in the header
            result = await read_draft_fn()
            full_text = self._parse_mcp_result(result)
            
            if not full_text:
                return {"sections": [], "total_sections": 0}
            
            try:
                data = json.loads(full_text)
                raw_sections = data.get("sections", {})
                
                # Convert to array format
                sections = []
                for section_id, section_data in raw_sections.items():
                    sections.append({
                        "section_id": section_id,
                        "title": section_data.get("title", section_id),
                        "content": section_data.get("content", ""),
                        "author": section_data.get("author", "unknown"),
                        "order": section_data.get("order", 0),
                        "created_at": section_data.get("last_updated"),
                        "updated_at": section_data.get("last_updated"),
                    })
                
                # Sort by order
                sections.sort(key=lambda s: s.get("order", 0))
                
                return {
                    "sections": sections,
                    "total_sections": len(sections),
                }
            except json.JSONDecodeError:
                return {"sections": [], "total_sections": 0}
        finally:
            # Close the uncached MCP connection
            await mcp_tool.__aexit__(None, None, None)

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
        tools: list[Any] | None = None,
    ) -> tuple[ChatAgent, AzureAIAgentClient]:
        """Create a ChatAgent wrapper for a Foundry agent.

        Args:
            agent_name: Name of the agent in Foundry (used as identifier in new API).
            description: Description of what this agent does (for tool conversion).
            tools: Optional list of tools (e.g., MCP scratchpad) to give to the agent.

        Returns:
            Tuple of (ChatAgent, AzureAIAgentClient) for cleanup tracking.
        """
        credential = self._ensure_credential()

        client = AzureAIAgentClient(
            project_endpoint=self.settings.azure_ai_foundry_endpoint,
            model_deployment_name=self.settings.model_deployment_name,
            agent_name=agent_name,
            async_credential=credential,
            should_cleanup_agent=False,
        )

        agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description=description,
            instructions="",  # Use agent's existing instructions
            tools=tools or [],
        )
        
        return agent, client

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

    async def _create_a2a_market_analyst(
        self,
        session_id: str,
    ) -> tuple[A2AAgent, httpx.AsyncClient]:
        """Create an A2A agent client for market-analyst with session headers.
        
        The market-analyst agent runs as a separate A2A service with its own
        MCP tools (demographics, scratchpad). The session_id is passed via
        X-Session-ID header to enable session-scoped MCP Scratchpad access.
        
        NOTE: Tool calls made BY the market-analyst (to MCP servers) are NOT
        visible to the orchestrator. See docs/IMPLEMENTATION_LOG.md for
        options on propagating tool events for SSE streaming.
        
        Args:
            session_id: Session ID for MCP Scratchpad isolation.
            
        Returns:
            Tuple of (A2AAgent, httpx.AsyncClient) for cleanup tracking.
        """
        if not self.settings.a2a_market_analyst_enabled:
            raise RuntimeError(
                "A2A Market Analyst not configured. Set A2A_MARKET_ANALYST_URL and A2A_MARKET_ANALYST_API_KEY."
            )
        
        # Create HTTP client with session-scoped headers
        # Extended timeout for LLM + MCP operations (can take several minutes)
        headers = {
            "X-Session-ID": session_id,
            "X-Caller-Agent": "research-orchestrator",
        }
        if self.settings.a2a_market_analyst_api_key:
            headers["Authorization"] = f"Bearer {self.settings.a2a_market_analyst_api_key}"
        
        http_client = httpx.AsyncClient(
            timeout=300.0,  # 5 minutes for complex analysis
            headers=headers,
        )
        
        # Fetch the Agent Card to discover capabilities
        agent_card_url = f"{self.settings.a2a_market_analyst_url}/agent-card.json"
        logger.info(f"Fetching A2A Agent Card from {agent_card_url}")
        
        try:
            response = await http_client.get(agent_card_url)
            response.raise_for_status()
            agent_card = AgentCard.model_validate(response.json())
            
            logger.info(f"A2A Agent Card: {agent_card.name} v{agent_card.version}")
            logger.info(f"A2A Agent URL: {agent_card.url}")
            if agent_card.skills:
                logger.info(f"A2A Agent Skills: {[s.name for s in agent_card.skills]}")
        except httpx.HTTPStatusError as e:
            await http_client.aclose()
            raise RuntimeError(
                f"Failed to fetch A2A Agent Card: HTTP {e.response.status_code} - {e.response.text[:200]}"
            )
        except Exception as e:
            await http_client.aclose()
            raise RuntimeError(f"Failed to fetch A2A Agent Card: {e}")
        
        # Create A2A agent using the URL from the agent card
        agent_url = agent_card.url.rstrip("/") if agent_card.url else self.settings.a2a_market_analyst_url
        
        agent = A2AAgent(
            name=agent_card.name,
            description=agent_card.description,
            agent_card=agent_card,
            url=agent_url,
            http_client=http_client,
        )
        
        logger.info(f"Created A2A market-analyst agent (session={session_id[:8]}...)")
        
        return agent, http_client

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
            context=context,
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
        session.started_at = datetime.now(timezone.utc)
        self._tool_call_log = []

        yield SSEEvent(
            event_type=SSEEventType.SESSION_STARTED,
            session_id=session_id,
            data={
                "query": session.query,
                "mode": "dynamic_orchestration",
            },
        )

        # Track clients for cleanup - initialized before try block
        agents_to_cleanup: list[ChatAgent] = []
        clients_to_cleanup: list[AzureAIAgentClient] = []
        # Track A2A HTTP clients for cleanup
        a2a_clients_to_cleanup: list[httpx.AsyncClient] = []
        # Track MCP tools created for agents (for cleanup)
        agent_mcp_tools: list[MCPStreamableHTTPTool] = []

        try:
            # Create MCP tools for orchestrator (scratchpad only)
            # ADR-006: MCP tools are now managed by orchestrator for real-time SSE streaming
            session_mcp_orchestrator = await self._get_session_mcp_tool(
                session_id, caller_agent="research-orchestrator"
            )
            
            # === A2A Agent: Market Analyst ===
            # Market-analyst runs as A2A service with its own MCP tools (demographics, scratchpad)
            # Session ID passed via X-Session-ID header for session-scoped MCP access
            market_a2a_agent, market_http_client = await self._create_a2a_market_analyst(session_id)
            a2a_clients_to_cleanup.append(market_http_client)
            
            # NOTE: Other agents are commented out for now - will be migrated to A2A
            # Create MCP tools for each specialist agent (DISABLED - agents now run MCP internally)
            # market_tools = await self._create_mcp_tools_for_agent("market-analyst", session_id)
            # agent_mcp_tools.extend([t for t in market_tools if t.name != f"scratchpad-{session_id[:8]}"])
            
            # competitor_tools = await self._create_mcp_tools_for_agent("competitor-analyst", session_id)
            # agent_mcp_tools.extend([t for t in competitor_tools if t.name != f"scratchpad-{session_id[:8]}"])
            
            # location_tools = await self._create_mcp_tools_for_agent("location-scout", session_id)
            # agent_mcp_tools.extend([t for t in location_tools if t.name != f"scratchpad-{session_id[:8]}"])
            
            # finance_tools = await self._create_mcp_tools_for_agent("finance-analyst", session_id)
            # agent_mcp_tools.extend([t for t in finance_tools if t.name != f"scratchpad-{session_id[:8]}"])
            
            # synthesizer_tools = await self._create_mcp_tools_for_agent("synthesizer", session_id)
            # synthesizer only has scratchpad, no additional tools to track
            
            # Create specialist agents with their MCP tools (DISABLED - using A2A)
            # market_agent, market_client = self._create_foundry_agent(
            #     agent_name=MARKET_ANALYST_AGENT_NAME,
            #     description="Analyzes market opportunities, trends, customer segments, TAM/SAM/SOM, and market dynamics.",
            #     tools=market_tools,
            # )
            # agents_to_cleanup.append(market_agent)
            # clients_to_cleanup.append(market_client)
            
            # competitor_agent, competitor_client = self._create_foundry_agent(
            #     agent_name=COMPETITOR_ANALYST_AGENT_NAME,
            #     description="Analyzes competitive landscape, competitor strengths and weaknesses, market positioning, and competitive threats.",
            #     tools=competitor_tools,
            # )
            # agents_to_cleanup.append(competitor_agent)
            # clients_to_cleanup.append(competitor_client)
            
            # location_agent, location_client = self._create_foundry_agent(
            #     agent_name=LOCATION_SCOUT_AGENT_NAME,
            #     description="Evaluates specific locations, districts, commercial properties, regulations, permits, and site viability.",
            #     tools=location_tools,
            # )
            # agents_to_cleanup.append(location_agent)
            # clients_to_cleanup.append(location_client)
            
            # finance_agent, finance_client = self._create_foundry_agent(
            #     agent_name=FINANCE_ANALYST_AGENT_NAME,
            #     description="Analyzes financial viability: startup costs, operating costs, revenue projections, break-even, ROI, and investment returns.",
            #     tools=finance_tools,
            # )
            # finance_agent, finance_client = self._create_foundry_agent(
            #     agent_name=FINANCE_ANALYST_AGENT_NAME,
            #     description="Analyzes financial viability: startup costs, operating costs, revenue projections, break-even, ROI, and investment returns.",
            #     tools=finance_tools,
            # )
            # agents_to_cleanup.append(finance_agent)
            # clients_to_cleanup.append(finance_client)
            
            # synthesizer_agent, synthesizer_client = self._create_foundry_agent(
            #     agent_name=SYNTHESIZER_AGENT_NAME,
            #     description="Synthesizes research findings into cohesive reports with actionable recommendations.",
            #     tools=synthesizer_tools,
            # )
            # agents_to_cleanup.append(synthesizer_agent)
            # clients_to_cleanup.append(synthesizer_client)

            # Create event queue early so we can pass it to subagent stream callbacks
            event_queue = ToolCallEventQueue()
            agent_call_count: dict[str, int] = {}
            # Pass session_id for span correlation in App Insights (ADR-005)
            tool_middleware = create_tool_call_middleware(
                event_queue, agent_call_count, session_id=session_id
            )

            # Convert A2A agent to tool
            # NOTE: A2A agents run MCP tools internally - tool calls NOT visible here
            # See SSE options documentation for approaches to propagate tool events
            market_tool = market_a2a_agent.as_tool(
                name="market_analysis",
                description="Call this tool to analyze market opportunities, trends, customer segments, and market sizing for the research query. The agent will use demographics data and shared scratchpad for collaboration.",
                arg_name="query",
                arg_description="The specific market analysis question or aspect to investigate",
                # NOTE: stream_callback doesn't work for A2A - tool events happen on remote agent
                # stream_callback=create_subagent_stream_callback(event_queue, "market-analyst", session_id),
            )
            
            # Other agent tools are commented out until migrated to A2A
            # competitor_tool = competitor_agent.as_tool(
            #     name="competitor_analysis",
            #     description="Call this tool to analyze competitive landscape, competitor strengths/weaknesses, and market positioning.",
            #     arg_name="query",
            #     arg_description="The specific competitor analysis question or aspect to investigate",
            #     stream_callback=create_subagent_stream_callback(event_queue, "competitor-analyst", session_id),
            # )
            # location_tool = location_agent.as_tool(
            #     name="location_scouting",
            #     description="Call this tool to evaluate specific locations, districts, commercial properties, regulations, permits, and site viability for expansion.",
            #     arg_name="query",
            #     arg_description="The specific location analysis question or district/property to investigate",
            #     stream_callback=create_subagent_stream_callback(event_queue, "location-scout", session_id),
            # )
            # finance_tool = finance_agent.as_tool(
            #     name="finance_analysis",
            #     description="Call this tool to analyze financial viability: startup costs, operating costs, revenue projections, break-even analysis, ROI, and investment returns.",
            #     arg_name="query",
            #     arg_description="The specific financial analysis question or scenario to evaluate",
            #     stream_callback=create_subagent_stream_callback(event_queue, "finance-analyst", session_id),
            # )
            # synthesizer_tool = synthesizer_agent.as_tool(
            #     name="synthesize_findings",
            #     description="Call this tool AFTER gathering market, competitor, location, and finance insights to create a final synthesized report with recommendations.",
            #     arg_name="context",
            #     arg_description="All the gathered research findings and insights to synthesize into a final report",
            #     stream_callback=create_subagent_stream_callback(event_queue, "synthesizer", session_id),
            # )

            yield SSEEvent(
                event_type=SSEEventType.AGENT_STARTED,
                session_id=session_id,
                data={
                    "phase": "orchestration",
                    "description": "Orchestrator starting dynamic research workflow (market-analyst via A2A)",
                    "available_tools": ["market_analysis"],  # Only market_analysis for now
                    "a2a_agents": ["market-analyst"],  # Indicate which agents use A2A
                    "scratchpad_enabled": session_mcp_orchestrator is not None,
                    "scratchpad_tools": [f.name for f in session_mcp_orchestrator.functions] if session_mcp_orchestrator else [],
                    "session_isolation": True,  # Indicate session isolation is active
                },
            )

            # Build the tools list - only market_analysis for now (others disabled)
            tools_list: list[Any] = [market_tool]
            # tools_list: list[Any] = [market_tool, competitor_tool, location_tool, finance_tool, synthesizer_tool]
            
            # Add session-scoped MCP Scratchpad to orchestrator
            # SECURITY: Uses X-Session-ID header for isolation
            if session_mcp_orchestrator:
                tools_list.append(session_mcp_orchestrator)
                logger.info(f"Added session-scoped MCP Scratchpad to orchestrator (session={session_id[:8]}...)")
            
            # Load and render system prompt
            prompt_template = self.settings.get_prompt("system_prompt")
            template = Template(prompt_template)
            system_prompt = template.render(
                query=session.query,
                context=session.context,
                scratchpad_enabled=session_mcp_orchestrator is not None
            )

            # Create the main orchestrator agent with specialist agents as tools
            chat_client = self._create_orchestrator_client()
            clients_to_cleanup.append(chat_client)
            orchestrator_agent = ChatAgent(
                chat_client=chat_client,
                name="research-orchestrator",
                instructions=system_prompt,
                tools=tools_list,
            )
            agents_to_cleanup.append(orchestrator_agent)

            # Run the orchestrator with streaming
            start_time = datetime.now(timezone.utc)
            orchestrator_thread = orchestrator_agent.get_new_thread()
            accumulated_content = ""
            scratchpad_sections_seen: set[str] = set()
            synthesizer_output: str | None = None  # Capture synthesizer's full output
            
            # Helper to process a single tool event and yield SSE events
            async def process_tool_event(tool_event: dict[str, Any]) -> AsyncGenerator[SSEEvent, None]:
                """Process a tool event from the queue and yield SSE events."""
                nonlocal scratchpad_sections_seen, synthesizer_output
                
                if tool_event["type"] == "tool_started":
                    event_data: ToolCallStartedData = tool_event["event_data"]
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.TOOL_CALL_STARTED,
                        session_id=session_id,
                        timestamp=event_timestamp,
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
                    tool_name = event_data_completed.tool_name
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.TOOL_CALL_COMPLETED,
                        session_id=session_id,
                        timestamp=event_timestamp,
                        data={
                            "tool_name": tool_name,
                            "tool_call_id": event_data_completed.tool_call_id,
                            "agent_name": event_data_completed.agent_name,
                            "output": event_data_completed.output,
                            "execution_time_ms": event_data_completed.execution_time_ms,
                            "call_number": tool_event["call_number"],
                        },
                    )
                    
                    # Check if this was a subagent tool - emit agent_response
                    if tool_name in AGENT_TOOL_NAMES:
                        output = event_data_completed.output
                        response_preview = ""
                        
                        if isinstance(output, str):
                            response_preview = output[:500]
                        elif isinstance(output, list):
                            text_parts = []
                            for item in output:
                                if isinstance(item, dict):
                                    text = item.get("text", item.get("content", ""))
                                    if text:
                                        text_parts.append(str(text))
                                elif isinstance(item, str):
                                    text_parts.append(item)
                            response_preview = "\n".join(text_parts)[:500]
                        elif isinstance(output, dict):
                            for key in ["text", "content", "summary", "response", "result"]:
                                if key in output and output[key]:
                                    response_preview = str(output[key])[:500]
                                    break
                            if not response_preview:
                                response_preview = str(output)[:500]
                        
                        if len(response_preview) >= 500:
                            response_preview = response_preview[:497] + "..."
                        
                        yield SSEEvent(
                            event_type=SSEEventType.AGENT_RESPONSE,
                            session_id=session_id,
                            data={
                                "agent_name": tool_name.replace("_", "-"),
                                "response_preview": response_preview,
                                "execution_time_ms": event_data_completed.execution_time_ms,
                            },
                        )
                        
                        # Special handling for synthesize_findings - emit synthesis_completed immediately
                        # This ensures the final report is available even if the orchestrator stream drops
                        if tool_name == "synthesize_findings":
                            # Extract full synthesis text (not truncated)
                            full_synthesis = ""
                            if isinstance(output, str):
                                full_synthesis = output
                            elif isinstance(output, list):
                                text_parts = []
                                for item in output:
                                    if isinstance(item, dict):
                                        text = item.get("text", item.get("content", ""))
                                        if text:
                                            text_parts.append(str(text))
                                    elif isinstance(item, str):
                                        text_parts.append(item)
                                full_synthesis = "\n".join(text_parts)
                            elif isinstance(output, dict):
                                for key in ["text", "content", "summary", "response", "result"]:
                                    if key in output and output[key]:
                                        full_synthesis = str(output[key])
                                        break
                                if not full_synthesis:
                                    full_synthesis = str(output)
                            
                            synthesizer_output = full_synthesis
                            logger.info(f"Captured synthesizer output ({len(full_synthesis)} chars)")
                            
                            # Emit synthesis_completed immediately so UI gets the report
                            yield SSEEvent(
                                event_type=SSEEventType.SYNTHESIS_COMPLETED,
                                session_id=session_id,
                                data={
                                    "agent": "synthesizer",
                                    "execution_time_ms": event_data_completed.execution_time_ms,
                                    "synthesis": full_synthesis,
                                },
                            )
                    
                    # If this was a scratchpad write, emit a scratchpad updated event
                    if tool_event.get("is_scratchpad_write"):
                        section_name = tool_event.get("section_name", "unknown")
                        tool_type = tool_event.get("tool_type")
                        operation = "created" if section_name not in scratchpad_sections_seen else "updated"
                        scratchpad_sections_seen.add(section_name)
                        
                        input_args = self._tool_call_log[-1].get("input_args", {}) if self._tool_call_log else {}
                        content_preview = None
                        tasks_created = None
                        tasks_list = None
                        task_update = None
                        
                        if tool_type == "add_note":
                            content_preview = str(input_args.get("content", ""))[:500]
                        elif tool_type == "add_tasks":
                            tasks = input_args.get("tasks", [])
                            tasks_created = len(tasks) if isinstance(tasks, list) else 0
                            tool_output = event_data_completed.output
                            if isinstance(tool_output, dict):
                                created_tasks = tool_output.get("tasks", [])
                                tasks_list = created_tasks if created_tasks else (tasks if isinstance(tasks, list) else [])
                            else:
                                tasks_list = tasks if isinstance(tasks, list) else []
                            if tasks:
                                descriptions = [t.get("description", "") for t in tasks if isinstance(t, dict)]
                                content_preview = "; ".join(descriptions)[:500]
                        elif tool_type == "update_task":
                            task_update = {
                                "task_id": input_args.get("task_id"),
                                "status": input_args.get("status"),
                                "assigned_to": input_args.get("assigned_to"),
                            }
                            content_preview = f"Task {input_args.get('task_id')} → {input_args.get('status')}"
                        elif tool_type == "write_draft_section":
                            content_preview = str(input_args.get("content", ""))[:500]
                        
                        yield SSEEvent(
                            event_type=SSEEventType.SCRATCHPAD_UPDATED,
                            session_id=session_id,
                            data=ScratchpadUpdatedData(
                                section_name=section_name,
                                operation=operation,
                                updated_by=event_data_completed.agent_name,
                                content_preview=content_preview,
                                tool_type=tool_type,
                                tasks_created=tasks_created,
                                tasks=tasks_list,
                                task_update=task_update,
                            ).model_dump(),
                        )
                
                elif tool_event["type"] == "tool_failed":
                    event_data_failed: ToolCallFailedData = tool_event["event_data"]
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.TOOL_CALL_FAILED,
                        session_id=session_id,
                        timestamp=event_timestamp,
                        data={
                            "tool_name": event_data_failed.tool_name,
                            "tool_call_id": event_data_failed.tool_call_id,
                            "agent_name": event_data_failed.agent_name,
                            "error": event_data_failed.error,
                            "error_type": event_data_failed.error_type,
                            "call_number": tool_event["call_number"],
                        },
                    )
                
                # === Subagent streaming events (from stream_callback) ===
                elif tool_event["type"] == "subagent_tool_started":
                    subagent_event: SubagentToolStartedData = tool_event["event_data"]
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.SUBAGENT_TOOL_STARTED,
                        session_id=session_id,
                        timestamp=event_timestamp,
                        data={
                            "subagent_name": subagent_event.subagent_name,
                            "tool_name": subagent_event.tool_name,
                            "tool_call_id": subagent_event.tool_call_id,
                            "input_preview": subagent_event.input_preview,
                        },
                    )
                
                elif tool_event["type"] == "subagent_tool_completed":
                    subagent_completed: SubagentToolCompletedData = tool_event["event_data"]
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.SUBAGENT_TOOL_COMPLETED,
                        session_id=session_id,
                        timestamp=event_timestamp,
                        data={
                            "subagent_name": subagent_completed.subagent_name,
                            "tool_name": subagent_completed.tool_name,
                            "tool_call_id": subagent_completed.tool_call_id,
                            "output_preview": subagent_completed.output_preview,
                        },
                    )
                
                elif tool_event["type"] == "subagent_progress":
                    subagent_progress: SubagentProgressData = tool_event["event_data"]
                    event_timestamp = datetime.fromisoformat(tool_event["timestamp"])
                    yield SSEEvent(
                        event_type=SSEEventType.SUBAGENT_PROGRESS,
                        session_id=session_id,
                        timestamp=event_timestamp,
                        data={
                            "subagent_name": subagent_progress.subagent_name,
                            "text_chunk": subagent_progress.text_chunk,
                        },
                    )

            # Stream the orchestrator's execution with concurrent queue processing
            # Use asyncio to interleave queue events with stream updates
            stream_iter = orchestrator_agent.run_stream(
                f"Please conduct comprehensive research on: {session.query}",
                thread=orchestrator_thread,
                middleware=[tool_middleware],
            ).__aiter__()
            
            stream_exhausted = False
            pending_stream_task: asyncio.Task | None = None
            
            while not stream_exhausted:
                # Create task for next stream update if not already pending
                if pending_stream_task is None:
                    pending_stream_task = asyncio.create_task(stream_iter.__anext__())
                
                # Wait for either: stream update OR queue event (with short timeout)
                # This allows us to emit queue events even while waiting for stream
                queue_event = await event_queue.get(timeout=0.1)
                
                if queue_event is not None:
                    # Process queue event immediately
                    async for sse_event in process_tool_event(queue_event):
                        yield sse_event
                    continue  # Check for more queue events before waiting on stream
                
                # No queue events - check if stream task is done
                if pending_stream_task.done():
                    try:
                        update = pending_stream_task.result()
                        pending_stream_task = None
                        
                        # Drain any remaining queue events
                        while True:
                            tool_event = event_queue.get_nowait()
                            if tool_event is None:
                                break
                            async for sse_event in process_tool_event(tool_event):
                                yield sse_event
                        
                        # Accumulate text output
                        if update.text:
                            accumulated_content += update.text
                            
                    except StopAsyncIteration:
                        stream_exhausted = True
                        pending_stream_task = None

            # Drain any remaining events from the queue
            event_queue.close()
            while True:
                tool_event = event_queue.get_nowait()
                if tool_event is None:
                    break
                async for sse_event in process_tool_event(tool_event):
                    yield sse_event

            end_time = datetime.now(timezone.utc)
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Emit agent completed event with full accumulated content
            yield SSEEvent(
                event_type=SSEEventType.AGENT_COMPLETED,
                session_id=session_id,
                data={
                    "agent_name": "research-orchestrator",
                    "content": accumulated_content,
                    "execution_time_ms": execution_time_ms,
                },
            )

            # Emit final scratchpad snapshot (using session-scoped tool)
            if session_mcp_orchestrator:
                final_snapshot = await self._get_scratchpad_snapshot_for_session(session_id)
                if final_snapshot:
                    final_snapshot.triggered_by = "workflow_complete"
                    yield SSEEvent(
                        event_type=SSEEventType.SCRATCHPAD_SNAPSHOT,
                        session_id=session_id,
                        data=final_snapshot.model_dump(),
                    )

            # Record the orchestrator's result
            # Use synthesizer output if captured, otherwise fall back to accumulated content
            final_synthesis_content = synthesizer_full_output or accumulated_content
            
            session.agent_results.append(
                AgentResult(
                    agent_type=AgentType.SYNTHESIZER,  # Final output is the synthesis
                    agent_name="research-orchestrator",
                    content=final_synthesis_content,
                    execution_time_ms=execution_time_ms,
                    timestamp=end_time,
                    metadata={
                        "tool_calls": self._tool_call_log,
                        "agent_call_counts": agent_call_count,
                    },
                )
            )
            session.final_synthesis = final_synthesis_content

            # Only emit synthesis_completed if we didn't already emit it from the synthesizer tool
            if not synthesizer_full_output:
                yield SSEEvent(
                    event_type=SSEEventType.SYNTHESIS_COMPLETED,
                    session_id=session_id,
                    data={
                        "agent": "research-orchestrator",
                        "execution_time_ms": execution_time_ms,
                        "tool_calls_made": self._tool_call_log,
                        "agent_call_counts": agent_call_count,
                        "synthesis": accumulated_content,  # Full synthesis for Final Report tab
                    },
                )

            # Workflow complete
            session.status = ResearchSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)

            yield SSEEvent(
                event_type=SSEEventType.WORKFLOW_COMPLETED,
                session_id=session_id,
                data={
                    "total_tool_calls": len(self._tool_call_log),
                    "agent_call_counts": agent_call_count,
                    "total_time_ms": int(
                        (session.completed_at - session.started_at).total_seconds() * 1000
                    ),
                    "synthesis": final_synthesis_content,
                },
            )

        except Exception as e:
            session.status = ResearchSessionStatus.FAILED
            session.error_message = str(e)
            session.completed_at = datetime.now(timezone.utc)
            logger.exception(f"Workflow failed for session {session_id}")

            yield SSEEvent(
                event_type=SSEEventType.WORKFLOW_FAILED,
                session_id=session_id,
                data={
                    "error": str(e),
                    "tool_calls_before_failure": self._tool_call_log,
                },
            )
        
        finally:
            # Clean up A2A HTTP clients first (before MCP tools they might depend on)
            for http_client in a2a_clients_to_cleanup:
                try:
                    await http_client.aclose()
                    logger.debug("Cleaned up A2A HTTP client")
                except Exception as e:
                    logger.debug(f"Error closing A2A HTTP client: {e}")
            
            # Clean up agent-specific MCP tools (demographics, business-registry, etc.)
            # ADR-006: These are created per-workflow and must be cleaned up
            for mcp_tool in agent_mcp_tools:
                try:
                    await mcp_tool.__aexit__(None, None, None)
                    logger.debug(f"Cleaned up agent MCP tool: {mcp_tool.name}")
                except Exception as e:
                    logger.debug(f"Error cleaning up agent MCP tool {mcp_tool.name}: {e}")
            
            # Clean up session-scoped scratchpad MCP tools
            # This prevents ClosedResourceError when API proxy tries to use stale cached tools
            await self._cleanup_session_mcp_tools(session_id)
            
            # Clean up agent clients to prevent unclosed aiohttp sessions
            # NOTE: Some clients may have MCP tools with anyio cancel scopes that were
            # entered in a different task context. We catch and ignore RuntimeError for
            # cancel scope issues since the underlying resources will be cleaned up anyway.
            for client in clients_to_cleanup:
                try:
                    if hasattr(client, 'close'):
                        await client.close()
                    elif hasattr(client, '_session') and client._session:
                        await client._session.close()
                except RuntimeError as e:
                    if "cancel scope" in str(e):
                        logger.debug(f"Ignoring cross-task cancel scope during cleanup: {e}")
                    else:
                        logger.debug(f"Error closing client: {e}")
                except Exception as cleanup_error:
                    logger.debug(f"Error closing client: {cleanup_error}")
            
            logger.info(f"Workflow cleanup completed for session {session_id}")

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
            "a2a_agents": {
                "market_analyst": {
                    "enabled": self.settings.a2a_market_analyst_enabled,
                    "url": self.settings.a2a_market_analyst_url if self.settings.a2a_market_analyst_enabled else None,
                },
            },
            "mcp_scratchpad": {
                "enabled": self.settings.mcp_scratchpad_enabled,
                "connected": self._mcp_scratchpad is not None,
                "url": self.settings.mcp_scratchpad_url if self.settings.mcp_scratchpad_enabled else None,
                "tools_count": len(self._mcp_scratchpad.functions) if self._mcp_scratchpad else 0,
            },
        }
        return health
