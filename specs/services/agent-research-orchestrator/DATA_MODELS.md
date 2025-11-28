# Service Data Models: agent-research-orchestrator

Schemas owned by the research orchestrator service.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| ResearchSession | Domain Model | agent-research-orchestrator | This service | 1.0 |
| ResearchRequest | API Request | agent-research-orchestrator | This service | 1.0 |
| AgentActivityEvent | SSE Event | agent-research-orchestrator | This service | 1.0 |
| WorkflowState | Internal State | agent-research-orchestrator | This service | 1.0 |

## Detailed Schemas

### ResearchSession

**Purpose**: Represents an active research session with workflow state.

**Lifecycle**: Created on POST /research/sessions, updated during workflow, archived on completion.

**Storage**: In-memory (demo scope), could be persisted to Cosmos DB for production.

```python
class ResearchSession(BaseModel):
    """Active research session."""
    id: str = Field(description="Unique session identifier (UUID)")
    query: str = Field(description="Original user research question")
    status: Literal["created", "running", "waiting_input", "completed", "failed"]
    created_at: datetime
    updated_at: datetime
    current_agent: str | None = Field(description="Currently executing agent name")
    checklist: list[ChecklistItem] = Field(default_factory=list)
    pending_questions: list[Question] = Field(default_factory=list)
    final_report: str | None = None
    error: str | None = None

class ChecklistItem(BaseModel):
    id: int
    task: str
    agent: str
    status: Literal["pending", "in_progress", "completed", "skipped"]
    notes: str | None = None

class Question(BaseModel):
    id: str
    question: str
    context: str
    priority: Literal["high", "medium", "low"]
    answer: str | None = None
```

**Example Payload**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "Should Cofilot expand to Vienna?",
  "status": "running",
  "created_at": "2025-11-27T10:00:00Z",
  "updated_at": "2025-11-27T10:05:30Z",
  "current_agent": "market-analyst",
  "checklist": [
    {"id": 1, "task": "Market research", "agent": "market-analyst", "status": "in_progress"},
    {"id": 2, "task": "Competitor analysis", "agent": "competitor-analyst", "status": "pending"}
  ],
  "pending_questions": [],
  "final_report": null
}
```

### ResearchRequest

**Purpose**: API request to start a research session.

```python
class ResearchRequest(BaseModel):
    """Request to start research."""
    query: str = Field(min_length=10, max_length=1000, description="Research question")
    context: dict[str, Any] | None = Field(default=None, description="Optional context")
```

### AgentActivityEvent

**Purpose**: SSE event for real-time UI updates.

```python
class AgentActivityEvent(BaseModel):
    """SSE event payload."""
    event_type: Literal[
        "session_started",
        "agent_started",
        "agent_completed",
        "questions_pending",
        "progress_update",
        "research_complete",
        "error"
    ]
    session_id: str
    timestamp: datetime
    agent: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None
```

**Example Payload**:
```json
{
  "event_type": "agent_started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-27T10:05:30Z",
  "agent": "market-analyst",
  "message": "Starting market analysis for Vienna",
  "data": {"checklist_item": 1}
}
```

### WorkflowState

**Purpose**: Internal state machine for workflow execution.

```python
class WorkflowState(BaseModel):
    """Internal workflow state."""
    phase: Literal["init", "gathering", "synthesizing", "complete", "error"]
    agents_completed: list[str]
    agents_pending: list[str]
    retry_count: dict[str, int]
    scratchpad_session_id: str
```

## Validation Rules

| Field | Rule |
|-------|------|
| ResearchRequest.query | 10-1000 chars, no script tags |
| ResearchSession.id | Valid UUID v4 |
| AgentActivityEvent.timestamp | ISO 8601 format |

## Shared Contract References

- `ChecklistItem` schema shared with `mcp-scratchpad`
- `Question` schema shared with `mcp-scratchpad`
- See `../../platform/DATA_MODELS.md` for canonical event schemas
