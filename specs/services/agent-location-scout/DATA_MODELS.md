# Service Data Models: agent-location-scout

Schemas used by the location-scout agent.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| LocationAnalysisRequest | Agent Input | Foundry Runtime | Foundry Protocol | 1.0 |
| LocationAnalysisResult | Agent Output | agent-location-scout | This service | 1.0 |
| Neighborhood | Domain Model | mcp-location | mcp-location | 1.0 |
| Regulation | Domain Model | mcp-location | mcp-location | 1.0 |

## Detailed Schemas

### LocationAnalysisRequest

**Purpose**: Input to the agent via Foundry Responses API.

**Source**: Foundry protocol - standard message format.

```python
# Received via Foundry Responses API
class AgentInput(BaseModel):
    """Standard Foundry agent input."""
    messages: list[Message]
    
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
```

### LocationAnalysisResult

**Purpose**: Structured output from location analysis.

**Storage**: Written to mcp-scratchpad.

```python
class LocationAnalysisResult(BaseModel):
    """Location analysis findings."""
    city: str
    analysis_date: datetime
    neighborhoods: list[NeighborhoodAssessment]
    regulations_summary: str
    recommended_locations: list[str]
    risks: list[str]
    overall_score: float = Field(ge=0, le=10)

class NeighborhoodAssessment(BaseModel):
    name: str
    rent_per_sqm: float
    foot_traffic: Literal["low", "medium", "high"]
    competition_density: int
    demographic_fit: float = Field(ge=0, le=10)
    pros: list[str]
    cons: list[str]
    score: float = Field(ge=0, le=10)
```

**Example Payload** (written to scratchpad):
```json
{
  "city": "Vienna",
  "analysis_date": "2025-11-27T10:00:00Z",
  "neighborhoods": [
    {
      "name": "Innere Stadt",
      "rent_per_sqm": 45.0,
      "foot_traffic": "high",
      "competition_density": 8,
      "demographic_fit": 7.5,
      "pros": ["High visibility", "Tourist traffic", "Affluent customers"],
      "cons": ["Expensive rent", "High competition"],
      "score": 7.2
    }
  ],
  "regulations_summary": "Vienna requires...",
  "recommended_locations": ["Innere Stadt", "Neubau"],
  "risks": ["High rent costs", "Saturated market in center"],
  "overall_score": 7.0
}
```

### Neighborhood (from mcp-location)

**Purpose**: Raw neighborhood data from MCP server.

```python
class Neighborhood(BaseModel):
    id: str
    name: str
    city: str
    district: str
    rent_per_sqm: float
    foot_traffic_index: int  # 1-100
    demographics: Demographics
    competition_count: int

class Demographics(BaseModel):
    population: int
    median_age: float
    median_income: float
    student_percentage: float
```

### Regulation (from mcp-location)

**Purpose**: Business regulation information.

```python
class Regulation(BaseModel):
    id: str
    jurisdiction: str
    category: str  # permits, health, zoning, labor
    title: str
    description: str
    requirements: list[str]
    estimated_timeline: str
    estimated_cost: float | None
```

## Validation Rules

| Field | Rule |
|-------|------|
| overall_score | 0.0 - 10.0 |
| rent_per_sqm | > 0 |
| foot_traffic | enum: low, medium, high |

## Shared Contract References

- `Neighborhood` schema defined by `mcp-location`
- `Regulation` schema defined by `mcp-location`
- Scratchpad section schema shared with all agents
