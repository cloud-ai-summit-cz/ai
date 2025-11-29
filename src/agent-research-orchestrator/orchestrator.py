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

Session Isolation (SECURITY):
- Each research session gets a unique session_id
- MCP Scratchpad tools are wrapped with session-scoped headers
- AI agents CANNOT set or modify session_id - it's injected by the orchestrator
- This prevents cross-session data access

Uses middleware to intercept tool calls for real-time SSE streaming.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
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
    
    def close(self) -> None:
        """Mark the queue as closed."""
        self._closed = True


# Scratchpad tool names for tracking updates
SCRATCHPAD_WRITE_TOOLS = {"write_draft_section", "add_note", "add_task", "add_tasks", "update_task"}
SCRATCHPAD_READ_TOOLS = {"read_section", "list_sections"}
SCRATCHPAD_QUESTION_TOOLS = {"add_question", "get_pending_questions", "get_answered_questions", "submit_answers"}

# Agent tool names (subagents exposed as tools to orchestrator)
AGENT_TOOL_NAMES = {"market_analysis", "competitor_analysis", "synthesize_findings"}


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_scratchpad_write": function_name in SCRATCHPAD_WRITE_TOOLS,
            "is_scratchpad_question": function_name in SCRATCHPAD_QUESTION_TOOLS,
        })
        
        logger.info(f"Tool call started: {function_name} (call #{call_number}) args={input_args}")
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
            logger.error(f"Tool call failed: {function_name} - {error_message}")
            raise
        finally:
            end_time = datetime.now(timezone.utc)
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
                
                logger.info(f"Tool call completed: {function_name} in {execution_time_ms}ms")
    
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
        self._session_mcp_tools: dict[str, MCPStreamableHTTPTool] = {}  # Session-scoped MCP tools

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
        # Clean up session-scoped MCP tools
        for session_id, mcp_tool in list(self._session_mcp_tools.items()):
            try:
                await mcp_tool.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.debug(f"Error closing session MCP tool {session_id}: {e}")
        self._session_mcp_tools.clear()
        
        # Clean up base MCP Scratchpad
        if self._mcp_scratchpad:
            await self._mcp_scratchpad.__aexit__(exc_type, exc_val, exc_tb)
            self._mcp_scratchpad = None
        
        if self._credential:
            await self._credential.close()

    async def _get_session_mcp_tool(
        self,
        session_id: str,
        caller_agent: str = "orchestrator",
    ) -> MCPStreamableHTTPTool | None:
        """Get or create a session-scoped MCP tool with session headers.
        
        SECURITY: This method creates MCP tool connections that include
        the X-Session-ID header. AI agents cannot modify this header.
        
        Args:
            session_id: The session ID for isolation.
            caller_agent: The agent name for audit logging.
            
        Returns:
            Session-scoped MCP tool, or None if scratchpad not configured.
        """
        if not self.settings.mcp_scratchpad_enabled:
            return None
        
        # Create a unique key for this session+agent combination
        cache_key = f"{session_id}:{caller_agent}"
        
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
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy")
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
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
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy")
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
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
        mcp_tool = await self._get_session_mcp_tool(session_id, caller_agent="api-proxy")
        if not mcp_tool:
            raise RuntimeError("MCP Scratchpad not configured")
        
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

        try:
            # Create session-scoped MCP scratchpad tools with X-Session-ID header
            # SECURITY: This ensures each session's data is isolated
            session_mcp_orchestrator = await self._get_session_mcp_tool(
                session_id, caller_agent="research-orchestrator"
            )
            session_mcp_market = await self._get_session_mcp_tool(
                session_id, caller_agent="market-analyst"
            )
            session_mcp_competitor = await self._get_session_mcp_tool(
                session_id, caller_agent="competitor-analyst"
            )
            session_mcp_synthesizer = await self._get_session_mcp_tool(
                session_id, caller_agent="synthesizer"
            )
            
            # Create specialist agents with session-scoped MCP scratchpad access
            # Each agent gets its own MCP tool with appropriate X-Caller-Agent header
            market_agent, market_client = self._create_foundry_agent(
                agent_name=MARKET_ANALYST_AGENT_NAME,
                description="Analyzes market opportunities, trends, customer segments, TAM/SAM/SOM, and market dynamics.",
                tools=[session_mcp_market] if session_mcp_market else [],
            )
            agents_to_cleanup.append(market_agent)
            clients_to_cleanup.append(market_client)
            
            competitor_agent, competitor_client = self._create_foundry_agent(
                agent_name=COMPETITOR_ANALYST_AGENT_NAME,
                description="Analyzes competitive landscape, competitor strengths and weaknesses, market positioning, and competitive threats.",
                tools=[session_mcp_competitor] if session_mcp_competitor else [],
            )
            agents_to_cleanup.append(competitor_agent)
            clients_to_cleanup.append(competitor_client)
            
            synthesizer_agent, synthesizer_client = self._create_foundry_agent(
                agent_name=SYNTHESIZER_AGENT_NAME,
                description="Synthesizes research findings into cohesive reports with actionable recommendations.",
                tools=[session_mcp_synthesizer] if session_mcp_synthesizer else [],
            )
            agents_to_cleanup.append(synthesizer_agent)
            clients_to_cleanup.append(synthesizer_client)

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
                    "scratchpad_enabled": session_mcp_orchestrator is not None,
                    "scratchpad_tools": [f.name for f in session_mcp_orchestrator.functions] if session_mcp_orchestrator else [],
                    "session_isolation": True,  # Indicate session isolation is active
                },
            )

            # Create event queue and middleware for tool call interception
            event_queue = ToolCallEventQueue()
            agent_call_count: dict[str, int] = {}
            tool_middleware = create_tool_call_middleware(event_queue, agent_call_count)

            # Build the tools list - agent tools + session-scoped MCP scratchpad
            tools_list: list[Any] = [market_tool, competitor_tool, synthesizer_tool]
            
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
                        tool_name = event_data_completed.tool_name
                        
                        yield SSEEvent(
                            event_type=SSEEventType.TOOL_CALL_COMPLETED,
                            session_id=session_id,
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
                        # so UI knows to poll scratchpad for updated notes/draft
                        if tool_name in AGENT_TOOL_NAMES:
                            # Extract a response summary from the tool output
                            output = event_data_completed.output
                            response_summary = ""
                            if isinstance(output, str):
                                response_summary = output[:200] + ("..." if len(output) > 200 else "")
                            elif isinstance(output, dict):
                                response_summary = output.get("summary", output.get("response", str(output)))[:200]
                            
                            yield SSEEvent(
                                event_type=SSEEventType.AGENT_RESPONSE,
                                session_id=session_id,
                                data={
                                    "agent_name": tool_name.replace("_", "-"),
                                    "response_summary": response_summary,
                                    "execution_time_ms": event_data_completed.execution_time_ms,
                                },
                            )
                        
                        # If this was a scratchpad write, emit a scratchpad updated event
                        if tool_event.get("is_scratchpad_write"):
                            section_name = tool_event.get("section_name", "unknown")
                            tool_type = tool_event.get("tool_type")
                            operation = "created" if section_name not in scratchpad_sections_seen else "updated"
                            scratchpad_sections_seen.add(section_name)
                            
                            # Extract content preview from input args
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
                                
                                # Try to extract created tasks with IDs from tool output
                                tool_output = event_data_completed.output
                                if isinstance(tool_output, dict):
                                    created_tasks = tool_output.get("tasks", [])
                                    if created_tasks:
                                        # Use output tasks (have server-assigned IDs)
                                        tasks_list = created_tasks
                                    else:
                                        # Fallback to input tasks
                                        tasks_list = tasks if isinstance(tasks, list) else []
                                else:
                                    tasks_list = tasks if isinstance(tasks, list) else []
                                    
                                # Create preview from task descriptions (still useful for logging)
                                if tasks:
                                    descriptions = [t.get("description", "") for t in tasks if isinstance(t, dict)]
                                    content_preview = "; ".join(descriptions)[:500]
                            elif tool_type == "update_task":
                                # Send the task update details
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

                # Accumulate text output silently - no streaming events
                # We'll emit one final message when the workflow completes
                if update.text:
                    accumulated_content += update.text

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
                    "synthesis": accumulated_content,
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
            # Clean up agent clients to prevent unclosed aiohttp sessions
            for client in clients_to_cleanup:
                try:
                    if hasattr(client, 'close'):
                        await client.close()
                    elif hasattr(client, '_session') and client._session:
                        await client._session.close()
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
            "mcp_scratchpad": {
                "enabled": self.settings.mcp_scratchpad_enabled,
                "connected": self._mcp_scratchpad is not None,
                "url": self.settings.mcp_scratchpad_url if self.settings.mcp_scratchpad_enabled else None,
                "tools_count": len(self._mcp_scratchpad.functions) if self._mcp_scratchpad else 0,
            },
        }
        return health
