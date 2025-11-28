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

    SESSION_STARTED = "session_started"
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"       # Streaming text chunks from agent
    AGENT_THINKING = "agent_thinking"       # Agent is processing
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_PROGRESS = "synthesis_progress"  # Streaming text chunks from synthesizer
    SYNTHESIS_COMPLETED = "synthesis_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    event_type: SSEEventType
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as SSE message."""
        return f"event: {self.event_type.value}\ndata: {self.model_dump_json()}\n\n"


# === Health Check Models ===


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    foundry_endpoint: str
    model_deployment: str
