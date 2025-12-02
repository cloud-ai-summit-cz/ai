"""Data models for Research Orchestrator API."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ResearchSessionStatus(str, Enum):
    """Status of a research session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Types of agents in the research workflow."""

    MARKET_ANALYST = "market-analyst"
    COMPETITOR_ANALYST = "competitor-analyst"
    SYNTHESIZER = "synthesizer"


# === Request Models ===


class CreateSessionRequest(BaseModel):
    """Request to create a new research session."""

    query: str = Field(
        description="The research query to investigate",
        max_length=2000,
        examples=["Analyze the market opportunity for a new coffee shop in Prague 2"],
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional context to provide to agents",
    )


class StartSessionRequest(BaseModel):
    """Request to start executing a research session."""

    # Currently empty, but can be extended for additional options
    pass


# === Response Models ===


class AgentResult(BaseModel):
    """Result from a single agent execution."""

    agent_type: AgentType
    agent_name: str
    content: str
    execution_time_ms: int
    timestamp: datetime = Field(default_factory=utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchSession(BaseModel):
    """A research session with its current state."""

    session_id: str = Field(description="Unique session identifier")
    query: str = Field(description="The original research query")
    context: dict[str, Any] | None = Field(default=None, description="Optional context for agents")
    status: ResearchSessionStatus = Field(description="Current session status")
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    agent_results: list[AgentResult] = Field(default_factory=list)
    final_synthesis: str | None = Field(default=None)
    error_message: str | None = Field(default=None)


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""

    sessions: list[ResearchSession]
    total: int


# === SSE Event Models (Trace-Based Architecture - ADR-005) ===


class SSEEventType(str, Enum):
    """Types of Server-Sent Events.
    
    Primary events are derived from Application Insights trace polling (ADR-005).
    Legacy events are still emitted by orchestrator for backward compatibility
    but frontend only processes the trace-based events.
    """

    # Workflow lifecycle (primary)
    WORKFLOW_STARTED = "workflow_started"       # Research session initialized
    WORKFLOW_COMPLETED = "workflow_completed"   # Research workflow finished successfully
    WORKFLOW_FAILED = "workflow_failed"         # Research workflow failed
    
    # Trace events from App Insights polling (primary)
    TRACE_SPAN_STARTED = "trace_span_started"     # Agent/operation span began
    TRACE_SPAN_COMPLETED = "trace_span_completed" # Agent/operation span ended
    TRACE_TOOL_CALL = "trace_tool_call"           # MCP tool call detected
    
    # Connection management
    HEARTBEAT = "heartbeat"                       # Keep-alive signal
    
    # Legacy events (emitted by orchestrator, not processed by new frontend)
    SESSION_STARTED = "session_started"
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_RESPONSE = "agent_response"
    SUBAGENT_TOOL_STARTED = "subagent_tool_started"
    SUBAGENT_TOOL_COMPLETED = "subagent_tool_completed"
    SUBAGENT_PROGRESS = "subagent_progress"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    SCRATCHPAD_UPDATED = "scratchpad_updated"
    SCRATCHPAD_SNAPSHOT = "scratchpad_snapshot"
    QUESTION_ADDED = "question_added"
    QUESTION_ANSWERED = "question_answered"
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_PROGRESS = "synthesis_progress"
    SYNTHESIS_COMPLETED = "synthesis_completed"


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: SSEEventType
    session_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as SSE message."""
        return f"event: {self.event_type.value}\ndata: {self.model_dump_json()}\n\n"


# === Trace Event Models (ADR-005: App Insights Polling) ===


class TraceSpanStartedData(BaseModel):
    """Data for TRACE_SPAN_STARTED event (from App Insights polling)."""
    
    span_id: str = Field(description="Unique span identifier")
    span_name: str = Field(description="Name of the span (e.g., 'MarketAnalyst.run')")
    parent_span_id: str | None = Field(default=None, description="Parent span ID if nested")
    operation_id: str = Field(description="Trace correlation ID")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")
    timestamp: str = Field(description="ISO timestamp when span started")


class TraceSpanCompletedData(BaseModel):
    """Data for TRACE_SPAN_COMPLETED event (from App Insights polling)."""
    
    span_id: str = Field(description="Unique span identifier")
    span_name: str = Field(description="Name of the span that completed")
    operation_id: str = Field(description="Trace correlation ID")
    duration_ms: int = Field(description="Span duration in milliseconds")
    status: str = Field(description="Completion status: 'success' or 'error'")
    error_message: str | None = Field(default=None, description="Error details if failed")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")
    timestamp: str = Field(description="ISO timestamp when span completed")


class TraceToolCallData(BaseModel):
    """Data for TRACE_TOOL_CALL event (MCP tool call from App Insights)."""
    
    span_id: str = Field(description="Unique span identifier")
    tool_name: str = Field(description="Name of the MCP tool called")
    tool_input: dict[str, Any] | None = Field(
        default=None, 
        description="Tool input (if ENABLE_SENSITIVE_DATA=true)"
    )
    tool_output: Any | None = Field(
        default=None, 
        description="Tool output (if ENABLE_SENSITIVE_DATA=true)"
    )
    operation_id: str = Field(description="Trace correlation ID")
    duration_ms: int | None = Field(default=None, description="Call duration if completed")
    status: str = Field(description="Status: 'started', 'completed', or 'error'")
    timestamp: str = Field(description="ISO timestamp of the call")


class WorkflowStartedData(BaseModel):
    """Data for WORKFLOW_STARTED event."""
    
    workflow_id: str = Field(description="Unique workflow execution identifier")
    query: str = Field(description="The research query being processed")


class WorkflowCompletedData(BaseModel):
    """Data for WORKFLOW_COMPLETED event."""
    
    workflow_id: str = Field(description="Workflow execution identifier")
    duration_ms: int = Field(description="Total workflow duration")
    final_report: dict[str, Any] | None = Field(
        default=None, 
        description="Synthesized research report"
    )


class WorkflowFailedData(BaseModel):
    """Data for WORKFLOW_FAILED event."""
    
    workflow_id: str | None = Field(default=None, description="Workflow identifier if available")
    error: str = Field(description="Error message")
    error_type: str = Field(description="Error classification")
    duration_ms: int | None = Field(default=None, description="Duration before failure")


class HeartbeatData(BaseModel):
    """Data for HEARTBEAT event."""
    
    polls_completed: int = Field(description="Number of App Insights polling cycles")


# === Internal Models (used by orchestrator, not exposed as SSE events) ===


class ToolCallStartedData(BaseModel):
    """Internal: Data for tool call tracking."""
    
    tool_name: str = Field(description="Name of the tool being called")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    input_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Input arguments passed to the tool"
    )


class ToolCallCompletedData(BaseModel):
    """Internal: Data for tool call completion tracking."""
    
    tool_name: str = Field(description="Name of the tool that completed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    output: Any = Field(description="Output returned by the tool")
    execution_time_ms: int = Field(description="Tool execution duration in milliseconds")


class ToolCallFailedData(BaseModel):
    """Internal: Data for tool call failure tracking."""
    
    tool_name: str = Field(description="Name of the tool that failed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    error: str = Field(description="Error message from the tool")
    error_type: str | None = Field(default=None, description="Exception type if available")


class SubagentToolStartedData(BaseModel):
    """Internal: Data for subagent tool call tracking."""
    
    subagent_name: str = Field(description="Name of the subagent making the tool call")
    tool_name: str = Field(description="Name of the tool being called")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    input_preview: str | None = Field(
        default=None,
        description="First 200 chars of tool input arguments"
    )


class SubagentToolCompletedData(BaseModel):
    """Internal: Data for subagent tool completion tracking."""
    
    subagent_name: str = Field(description="Name of the subagent that made the tool call")
    tool_name: str = Field(description="Name of the tool that completed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    output_preview: str | None = Field(
        default=None,
        description="First 200 chars of tool output"
    )


class SubagentProgressData(BaseModel):
    """Internal: Data for subagent streaming progress."""
    
    subagent_name: str = Field(description="Name of the subagent generating content")
    text_chunk: str = Field(description="Text chunk from the subagent")


class ScratchpadSection(BaseModel):
    """Internal: A single section in the scratchpad."""
    
    name: str = Field(description="Section name/identifier")
    content: str = Field(description="Section content")
    updated_by: str | None = Field(default=None, description="Agent that last updated")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class ScratchpadSnapshotData(BaseModel):
    """Internal: Full scratchpad state (for orchestrator use)."""
    
    sections: list[ScratchpadSection] = Field(
        default_factory=list,
        description="All sections in the scratchpad"
    )
    total_sections: int = Field(description="Total number of sections")
    iteration: int | None = Field(default=None, description="Workflow iteration number")
    triggered_by: str | None = Field(
        default=None, 
        description="What triggered this snapshot"
    )


class ScratchpadUpdatedData(BaseModel):
    """Internal: Data for scratchpad updates (used by orchestrator logging)."""
    
    section_name: str = Field(description="Pillar/section that changed")
    operation: str = Field(description="Operation: 'created', 'updated', 'appended', 'deleted'")
    updated_by: str = Field(description="Agent that made the change")
    content_preview: str | None = Field(default=None, description="First 500 chars of new content")
    tool_type: str | None = Field(default=None, description="MCP tool that triggered this")
    tasks_created: int | None = Field(default=None, description="Number of tasks created")
    tasks: list[dict] | None = Field(default=None, description="Full task list for add_tasks tool")
    task_update: dict | None = Field(default=None, description="Task update details")


# === Health Check Models ===


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    foundry_endpoint: str
    model_deployment: str
