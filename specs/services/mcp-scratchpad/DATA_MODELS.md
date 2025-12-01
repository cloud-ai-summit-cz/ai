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
    state: WorkspaceState
    ttl: int = 86400  # 24 hours

class WorkspaceState(BaseModel):
    """The core state of the workspace."""
    notes: list[Note] = []
    draft_sections: dict[str, DraftSection] = {}
    plan: list[Task] = []

class Note(BaseModel):
    """A raw piece of information, fact, or finding."""
    id: str
    content: str
    author: str
    timestamp: datetime
    tags: list[str] = []

class DraftSection(BaseModel):
    """A structured section of the final report/output."""
    id: str
    title: str
    content: str
    author: str  # Agent who last updated this section
    last_updated: datetime
    version: int = 1

class Task(BaseModel):
    """A unit of work to be done."""
    id: str
    description: str
    status: str = "todo"  # todo, in_progress, completed, blocked
    assigned_to: str | None = None
    dependencies: list[str] = []
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

## Section Naming Conventions (Draft)

| Section ID | Title | Typical Author |
|------------|-------|----------------|
| `executive_summary` | Executive Summary | synthesizer |
| `market_analysis` | Market Analysis | market-analyst |
| `competitor_landscape` | Competitor Landscape | competitor-analyst |
| `financial_plan` | Financial Plan | finance-analyst |

## Note Tagging Conventions

| Tag | Usage |
|-----|-------|
| `pricing` | Pricing data, costs, fees |
| `competitor` | Competitor names, features, strengths |
| `regulation` | Laws, permits, zoning rules |
| `demographics` | Population stats, customer segments |
| `location` | Specific addresses, neighborhoods |
