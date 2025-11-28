# Service Data Models: agent-finance-analyst

Schemas used by the finance-analyst agent.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| A2ATask | A2A Protocol | A2A Standard | a2a-protocol.org | 1.0 |
| A2ATaskResult | A2A Protocol | A2A Standard | a2a-protocol.org | 1.0 |
| FinancialProjection | Domain Model | agent-finance-analyst | This service | 1.0 |
| StartupCosts | Domain Model | mcp-finance | mcp-finance | 1.0 |
| OperatingCosts | Domain Model | mcp-finance | mcp-finance | 1.0 |

## Detailed Schemas

### A2ATask (A2A Protocol Standard)

**Purpose**: Standard A2A task request.

```python
class A2ATask(BaseModel):
    """A2A protocol task."""
    id: str
    sessionId: str | None = None
    message: A2AMessage
    
class A2AMessage(BaseModel):
    role: Literal["user", "assistant"]
    parts: list[A2APart]
    
class A2APart(BaseModel):
    type: Literal["text", "file", "data"]
    text: str | None = None
    data: dict | None = None
```

### A2ATaskResult (A2A Protocol Standard)

**Purpose**: Standard A2A task response.

```python
class A2ATaskResult(BaseModel):
    """A2A protocol task result."""
    id: str
    status: A2ATaskStatus
    result: A2AMessage | None = None
    
class A2ATaskStatus(BaseModel):
    state: Literal["pending", "running", "completed", "failed", "canceled"]
    message: str | None = None
```

### FinancialProjection

**Purpose**: Complete financial analysis output.

**Storage**: Written to mcp-scratchpad.

```python
class FinancialProjection(BaseModel):
    """Complete financial analysis."""
    city: str
    analysis_date: datetime
    currency: str = "EUR"
    
    startup_costs: StartupCostsSummary
    operating_costs: OperatingCostsSummary
    revenue_projection: RevenueProjectionSummary
    break_even_analysis: BreakEvenAnalysis
    
    recommendation: str
    confidence_level: Literal["low", "medium", "high"]
    risks: list[str]
    assumptions: list[str]

class StartupCostsSummary(BaseModel):
    total: float
    breakdown: dict[str, float]  # category -> amount
    # renovation, equipment, permits, initial_inventory, marketing_launch

class OperatingCostsSummary(BaseModel):
    monthly_total: float
    breakdown: dict[str, float]  # category -> amount
    # rent, salaries, utilities, supplies, marketing, insurance

class RevenueProjectionSummary(BaseModel):
    monthly_average: float
    year_1_total: float
    year_2_total: float
    year_3_total: float
    growth_rate: float

class BreakEvenAnalysis(BaseModel):
    months_to_break_even: int
    break_even_monthly_revenue: float
    margin_of_safety: float
```

**Example Payload** (written to scratchpad):
```json
{
  "city": "Vienna",
  "analysis_date": "2025-11-27T10:00:00Z",
  "currency": "EUR",
  "startup_costs": {
    "total": 150000,
    "breakdown": {
      "renovation": 60000,
      "equipment": 40000,
      "permits": 5000,
      "initial_inventory": 15000,
      "marketing_launch": 30000
    }
  },
  "operating_costs": {
    "monthly_total": 25000,
    "breakdown": {
      "rent": 8000,
      "salaries": 12000,
      "utilities": 1500,
      "supplies": 2000,
      "marketing": 1000,
      "insurance": 500
    }
  },
  "revenue_projection": {
    "monthly_average": 35000,
    "year_1_total": 350000,
    "year_2_total": 420000,
    "year_3_total": 480000,
    "growth_rate": 0.15
  },
  "break_even_analysis": {
    "months_to_break_even": 18,
    "break_even_monthly_revenue": 28000,
    "margin_of_safety": 0.25
  },
  "recommendation": "Proceed with caution - moderate risk with good upside potential",
  "confidence_level": "medium",
  "risks": ["High initial investment", "Competitive market"],
  "assumptions": ["Foot traffic estimates based on location data", "Staff costs at Vienna average"]
}
```

## Validation Rules

| Field | Rule |
|-------|------|
| startup_costs.total | > 0 |
| months_to_break_even | > 0 |
| confidence_level | enum: low, medium, high |

## Shared Contract References

- A2A protocol schemas from a2a-protocol.org
- Scratchpad section schema shared with all agents
- Cost calculation schemas from `mcp-finance`
