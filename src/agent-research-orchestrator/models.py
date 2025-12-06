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
    language: str = Field(
        default="cs",
        description="Language for agent responses: 'cs' for Czech, 'en' for English",
        pattern="^(cs|en)$",
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
    language: str = Field(default="cs", description="Language for responses: 'cs' or 'en'")
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


# === SSE Event Models (ADR-007: Direct Orchestrator Events) ===


class SSEEventType(str, Enum):
    """Types of Server-Sent Events.
    
    ADR-007: UI events are now generated directly by the orchestrator middleware,
    providing real-time updates without the 2-5 second latency from App Insights polling.
    
    Primary events (sent to UI):
    - Workflow lifecycle: workflow_started, workflow_completed, workflow_failed
    - Agent operations: agent_started, agent_completed, agent_response, agent_progress
    - Tool calls: tool_call_started, tool_call_completed, tool_call_failed
    - Subagent operations: subagent_tool_started, subagent_tool_completed, subagent_progress
    - Scratchpad: scratchpad_updated, scratchpad_snapshot
    - Synthesis: synthesis_completed
    
    Observability-only events (NOT sent to UI, kept for potential future dashboards):
    - Trace events: trace_span_started, trace_span_completed, trace_tool_call
    """

    # Workflow lifecycle (primary)
    WORKFLOW_STARTED = "workflow_started"       # Research session initialized
    WORKFLOW_COMPLETED = "workflow_completed"   # Research workflow finished successfully
    WORKFLOW_FAILED = "workflow_failed"         # Research workflow failed
    
    # Agent operations (primary - from orchestrator)
    SESSION_STARTED = "session_started"
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_RESPONSE = "agent_response"
    
    # Subagent operations (primary - from stream_callback)
    SUBAGENT_TOOL_STARTED = "subagent_tool_started"
    SUBAGENT_TOOL_COMPLETED = "subagent_tool_completed"
    SUBAGENT_PROGRESS = "subagent_progress"
    
    # Tool calls (primary - from middleware)
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    
    # Scratchpad operations (primary - from middleware)
    SCRATCHPAD_UPDATED = "scratchpad_updated"
    SCRATCHPAD_SNAPSHOT = "scratchpad_snapshot"
    
    # Questions (primary - human-in-the-loop)
    QUESTION_ADDED = "question_added"
    AWAITING_USER_INPUT = "awaiting_user_input"
    QUESTIONS_ANSWERED = "questions_answered"
    
    # Synthesis (primary)
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_PROGRESS = "synthesis_progress"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    
    # Connection management
    HEARTBEAT = "heartbeat"                       # Keep-alive signal
    
    # Trace events (observability-only, NOT sent to UI - see ADR-007)
    TRACE_SPAN_STARTED = "trace_span_started"     # Agent/operation span began
    TRACE_SPAN_COMPLETED = "trace_span_completed" # Agent/operation span ended
    TRACE_TOOL_CALL = "trace_tool_call"           # MCP tool call detected


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: SSEEventType
    session_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as SSE message."""
        return f"event: {self.event_type.value}\ndata: {self.model_dump_json()}\n\n"


# === Trace Event Models (Observability-Only - ADR-007) ===
# NOTE: These events are NOT sent to the UI SSE stream.
# They are kept for potential future observability dashboards.
# UI events now come directly from the orchestrator middleware (ADR-007).


class TraceSpanStartedData(BaseModel):
    """Data for TRACE_SPAN_STARTED event (observability-only, not sent to UI)."""
    
    span_id: str = Field(description="Unique span identifier")
    span_name: str = Field(description="Name of the span (e.g., 'MarketAnalyst.run')")
    parent_span_id: str | None = Field(default=None, description="Parent span ID if nested")
    operation_id: str = Field(description="Trace correlation ID")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")
    timestamp: str = Field(description="ISO timestamp when span started")


class TraceSpanCompletedData(BaseModel):
    """Data for TRACE_SPAN_COMPLETED event (observability-only, not sent to UI)."""
    
    span_id: str = Field(description="Unique span identifier")
    span_name: str = Field(description="Name of the span that completed")
    operation_id: str = Field(description="Trace correlation ID")
    duration_ms: int = Field(description="Span duration in milliseconds")
    status: str = Field(description="Completion status: 'success' or 'error'")
    error_message: str | None = Field(default=None, description="Error details if failed")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Span attributes")
    timestamp: str = Field(description="ISO timestamp when span completed")


class TraceToolCallData(BaseModel):
    """Data for TRACE_TOOL_CALL event (observability-only, not sent to UI)."""
    
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


# === Tool Call Event Models (Primary SSE Events - ADR-007) ===
# These models are used for real-time SSE streaming to the UI.


class ToolCallStartedData(BaseModel):
    """Data for TOOL_CALL_STARTED event (sent to UI via SSE)."""
    
    tool_name: str = Field(description="Name of the tool being called")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    input_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Input arguments passed to the tool"
    )


class ToolCallCompletedData(BaseModel):
    """Data for TOOL_CALL_COMPLETED event (sent to UI via SSE)."""
    
    tool_name: str = Field(description="Name of the tool that completed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    output: Any = Field(description="Output returned by the tool")
    execution_time_ms: int = Field(description="Tool execution duration in milliseconds")


class ToolCallFailedData(BaseModel):
    """Data for TOOL_CALL_FAILED event (sent to UI via SSE)."""
    
    tool_name: str = Field(description="Name of the tool that failed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    error: str = Field(description="Error message from the tool")
    error_type: str | None = Field(default=None, description="Exception type if available")


class SubagentToolStartedData(BaseModel):
    """Data for SUBAGENT_TOOL_STARTED event (sent to UI via SSE)."""
    
    subagent_name: str = Field(description="Name of the subagent making the tool call")
    tool_name: str = Field(description="Name of the tool being called")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    input_preview: str | None = Field(
        default=None,
        description="First 200 chars of tool input arguments"
    )


class SubagentToolCompletedData(BaseModel):
    """Data for SUBAGENT_TOOL_COMPLETED event (sent to UI via SSE)."""
    
    subagent_name: str = Field(description="Name of the subagent that made the tool call")
    tool_name: str = Field(description="Name of the tool that completed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    output_preview: str | None = Field(
        default=None,
        description="First 200 chars of tool output"
    )


class SubagentProgressData(BaseModel):
    """Data for SUBAGENT_PROGRESS event (sent to UI via SSE)."""
    
    subagent_name: str = Field(description="Name of the subagent generating content")
    text_chunk: str = Field(description="Text chunk from the subagent")


# === Scratchpad Models (for SSE events and internal use) ===


class ScratchpadSection(BaseModel):
    """A single section in the scratchpad."""
    
    name: str = Field(description="Section name/identifier")
    content: str = Field(description="Section content")
    updated_by: str | None = Field(default=None, description="Agent that last updated")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class ScratchpadSnapshotData(BaseModel):
    """Full scratchpad state for SCRATCHPAD_SNAPSHOT event."""
    
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
    """Data for SCRATCHPAD_UPDATED event (sent to UI via SSE)."""
    
    section_name: str = Field(description="Pillar/section that changed")
    operation: str = Field(description="Operation: 'created', 'updated', 'appended', 'deleted'")
    updated_by: str = Field(description="Agent that made the change")
    content_preview: str | None = Field(default=None, description="First 500 chars of new content")
    tool_type: str | None = Field(default=None, description="MCP tool that triggered this")
    tasks_created: int | None = Field(default=None, description="Number of tasks created")
    tasks: list[dict] | None = Field(default=None, description="Full task list for add_tasks tool")
    task_update: dict | None = Field(default=None, description="Task update details")


# === Question Models (Human-in-the-Loop) ===


class QuestionPriority(str, Enum):
    """Priority level for a question."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


class Question(BaseModel):
    """A question from an agent to the user."""
    id: str = Field(description="Unique question ID")
    question: str = Field(description="The question text")
    context: str = Field(description="Why this information is needed")
    asked_by: str = Field(description="Agent that asked this question")
    priority: QuestionPriority = Field(description="Question priority level")
    asked_at: datetime = Field(description="When the question was asked")
    answered: bool = Field(default=False, description="Whether user has answered")
    answer: str | None = Field(default=None, description="User's answer if provided")
    answered_at: datetime | None = Field(default=None, description="When answered")


class QuestionAddedData(BaseModel):
    """Data for QUESTION_ADDED event (sent to UI via SSE)."""
    question: Question = Field(description="The question that was added")


class AwaitingUserInputData(BaseModel):
    """Data for AWAITING_USER_INPUT event (sent to UI via SSE).
    
    Emitted when the orchestrator blocks waiting for user input.
    """
    reason: str = Field(description="Why the workflow is waiting")
    blocking_question_ids: list[str] = Field(
        default_factory=list,
        description="IDs of questions that must be answered before proceeding"
    )


class QuestionsAnsweredData(BaseModel):
    """Data for QUESTIONS_ANSWERED event (sent to UI via SSE)."""
    answered_ids: list[str] = Field(description="IDs of questions that were answered")
    workflow_resumed: bool = Field(description="Whether answering unblocked the workflow")


class QuestionsResponse(BaseModel):
    """Response from GET /questions endpoint."""
    session_id: str
    questions: list[Question] = Field(default_factory=list)
    pending_count: int = Field(description="Number of unanswered questions")
    answered_count: int = Field(description="Number of answered questions")
    has_blocking_pending: bool = Field(description="True if any blocking questions unanswered")
    workflow_waiting: bool = Field(description="True if workflow is waiting for input")


class AnswerItem(BaseModel):
    """A single answer to a question."""
    question_id: str = Field(description="ID of the question being answered")
    answer: str = Field(description="The user's answer")


class AnswersRequest(BaseModel):
    """Request to submit answers to questions."""
    answers: list[AnswerItem] = Field(description="List of answers to submit")


class AnswersResponse(BaseModel):
    """Response from POST /answers endpoint."""
    session_id: str
    answers_saved: int = Field(description="Number of answers saved")
    workflow_unblocked: bool = Field(description="True if this unblocked the workflow")
    remaining_pending: int = Field(description="Number of questions still pending")


# === Health Check Models ===


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    foundry_endpoint: str
    model_deployment: str
