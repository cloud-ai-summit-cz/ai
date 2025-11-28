"""Data models for Research Orchestrator API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
        min_length=10,
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchSession(BaseModel):
    """A research session with its current state."""

    session_id: str = Field(description="Unique session identifier")
    query: str = Field(description="The original research query")
    status: ResearchSessionStatus = Field(description="Current session status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    agent_results: list[AgentResult] = Field(default_factory=list)
    final_synthesis: str | None = Field(default=None)
    error_message: str | None = Field(default=None)


class SessionListResponse(BaseModel):
    """Response containing a list of sessions."""

    sessions: list[ResearchSession]
    total: int


# === SSE Event Models ===


class SSEEventType(str, Enum):
    """Types of Server-Sent Events."""

    # Session lifecycle
    SESSION_STARTED = "session_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"       # Streaming text chunks from agent
    AGENT_THINKING = "agent_thinking"       # Agent is processing
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    
    # Tool events (detailed tool invocation tracking)
    TOOL_CALL_STARTED = "tool_call_started"     # Tool invocation started (with input)
    TOOL_CALL_COMPLETED = "tool_call_completed" # Tool completed (with output)
    TOOL_CALL_FAILED = "tool_call_failed"       # Tool failed (with error)
    
    # Scratchpad events (collaborative workspace updates)
    SCRATCHPAD_UPDATED = "scratchpad_updated"   # Section added/modified
    SCRATCHPAD_SNAPSHOT = "scratchpad_snapshot" # Full scratchpad state
    QUESTION_ADDED = "question_added"           # Human question queued
    QUESTION_ANSWERED = "question_answered"     # Human answered a question
    
    # Synthesis events
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_PROGRESS = "synthesis_progress"  # Streaming text chunks from synthesizer
    SYNTHESIS_COMPLETED = "synthesis_completed"


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: SSEEventType
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as SSE message."""
        return f"event: {self.event_type.value}\ndata: {self.model_dump_json()}\n\n"


# === Tool Call Event Models ===


class ToolCallStartedData(BaseModel):
    """Data for TOOL_CALL_STARTED event."""
    
    tool_name: str = Field(description="Name of the tool being called")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    input_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Input arguments passed to the tool"
    )


class ToolCallCompletedData(BaseModel):
    """Data for TOOL_CALL_COMPLETED event."""
    
    tool_name: str = Field(description="Name of the tool that completed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    output: Any = Field(description="Output returned by the tool")
    execution_time_ms: int = Field(description="Tool execution duration in milliseconds")


class ToolCallFailedData(BaseModel):
    """Data for TOOL_CALL_FAILED event."""
    
    tool_name: str = Field(description="Name of the tool that failed")
    tool_call_id: str = Field(description="Unique identifier for this tool invocation")
    agent_name: str = Field(description="Agent that initiated the tool call")
    error: str = Field(description="Error message from the tool")
    error_type: str | None = Field(default=None, description="Exception type if available")


# === Scratchpad Event Models ===


class ScratchpadSection(BaseModel):
    """A single section in the scratchpad."""
    
    name: str = Field(description="Section name/identifier")
    content: str = Field(description="Section content")
    updated_by: str | None = Field(default=None, description="Agent that last updated")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class ScratchpadUpdatedData(BaseModel):
    """Data for SCRATCHPAD_UPDATED event."""
    
    section_name: str = Field(description="Name of the section that changed")
    operation: str = Field(description="Operation: 'created', 'updated', 'appended', 'deleted'")
    updated_by: str = Field(description="Agent that made the change")
    content_preview: str | None = Field(
        default=None,
        description="First 500 chars of new content (for 'created'/'updated')"
    )
    appended_content: str | None = Field(
        default=None, 
        description="Content that was appended (for 'appended' operation)"
    )


class ScratchpadSnapshotData(BaseModel):
    """Data for SCRATCHPAD_SNAPSHOT event (full state after iteration)."""
    
    sections: list[ScratchpadSection] = Field(
        default_factory=list,
        description="All sections in the scratchpad"
    )
    total_sections: int = Field(description="Total number of sections")
    iteration: int | None = Field(default=None, description="Workflow iteration number")
    triggered_by: str | None = Field(
        default=None, 
        description="What triggered this snapshot (e.g., 'iteration_complete', 'agent_finished')"
    )


class QuestionData(BaseModel):
    """Data for question-related events."""
    
    question_id: str = Field(description="Unique question identifier")
    question: str = Field(description="The question text")
    asked_by: str = Field(description="Agent that asked the question")
    context: str | None = Field(default=None, description="Why the question was asked")
    answer: str | None = Field(default=None, description="Human's answer (for answered events)")
    answered_at: datetime | None = Field(default=None, description="When answered")


# === Health Check Models ===


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    foundry_endpoint: str
    model_deployment: str
