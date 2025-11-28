# Service Data Models: mcp-scratchpad

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| ScratchpadSession | Domain Model | mcp-scratchpad | This service | 1.0 |
| Section | Domain Model | mcp-scratchpad | This service | 1.0 |
| ChecklistItem | Domain Model | mcp-scratchpad | This service | 1.0 |
| Question | Domain Model | mcp-scratchpad | This service | 1.0 |

## Detailed Schemas

### ScratchpadSession

```python
class ScratchpadSession(BaseModel):
    """Session container for scratchpad data."""
    id: str  # Cosmos partition key
    session_id: str
    created_at: datetime
    updated_at: datetime
    sections: dict[str, Section]
    checklist: list[ChecklistItem]
    questions: list[Question]
    ttl: int = 86400  # 24 hours


class SectionStatus(str, Enum):
    """Status of a scratchpad section."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    NEEDS_REVIEW = "needs_review"
    COMPLETE = "complete"


class Section(BaseModel):
    """Named section in scratchpad with collaborative editing support."""
    name: str
    content: str
    status: SectionStatus = SectionStatus.DRAFT
    author: str  # Agent that created it
    contributors: list[str] = []  # Other agents that modified
    version: int = 1
    outline_position: int | None = None  # Position in final report (null if not part of report)
    created_at: datetime
    updated_at: datetime


class ChecklistItem(BaseModel):
    """Task tracking item."""
    id: str
    task: str
    agent: str
    status: Literal["pending", "in_progress", "completed", "failed"]
    updated_at: datetime
    notes: str | None = None


class QuestionPriority(str, Enum):
    """Priority level for human questions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Question(BaseModel):
    """Question queued for human review."""
    id: str
    question: str
    context: str  # Why this information is needed
    asked_by: str  # Agent that asked
    priority: QuestionPriority = QuestionPriority.MEDIUM
    blocking: bool = False  # If true, workflow should pause for this
    options: list[str] | None = None  # Optional multiple choice
    answer: str | None = None  # Human's answer (null until answered)
    created_at: datetime
    answered_at: datetime | None = None
```

## Storage Design (Demo Phase)

Data is stored in-memory using Python dictionaries:

```python
# In-memory session store
_sessions: dict[str, ScratchpadSession] = {}

# Access pattern
def get_session(session_id: str) -> ScratchpadSession | None:
    return _sessions.get(session_id)

def save_session(session: ScratchpadSession) -> None:
    _sessions[session.session_id] = session
```

**Limitations**:
- Data lost on service restart
- Single instance only (no horizontal scaling)
- No TTL enforcement (manual cleanup if needed)

> **Future (Production)**: Migrate to Cosmos DB with partition key `/session_id` and 24h TTL.

## Section Naming Conventions

| Section Name | Purpose | Typical Author |
|--------------|---------|----------------|
| `market_findings` | Market size, trends, customer segments | market-analyst |
| `competitor_analysis` | Competitor profiles, SWOT | competitor-analyst |
| `location_options` | Location evaluations, pros/cons | location-scout |
| `regulations` | Permits, zoning, compliance | location-scout |
| `financial_projections` | Startup costs, ROI, break-even | finance-analyst |
| `user_answers` | Collected answers from human | orchestrator |
| `final_report` | Synthesized final deliverable | synthesizer |

## Question Examples

```python
# High-priority blocking question
Question(
    id="q_001",
    question="What is your budget range for initial investment?",
    context="Required to calculate realistic financial projections and filter location options",
    asked_by="finance-analyst",
    priority=QuestionPriority.HIGH,
    blocking=True,
    options=["Under €50,000", "€50,000-€100,000", "€100,000-€200,000", "Over €200,000"],
)

# Medium-priority non-blocking question
Question(
    id="q_002",
    question="Do you have a preferred neighborhood in Prague?",
    context="Will prioritize analysis of specific areas if provided",
    asked_by="location-scout",
    priority=QuestionPriority.MEDIUM,
    blocking=False,
    options=None,  # Free-form answer
)
```
