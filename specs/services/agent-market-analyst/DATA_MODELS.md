# Service Data Models: agent-market-analyst

Schemas used by the market-analyst agent.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| MarketFindings | Domain Model | agent-market-analyst | This service | 1.0 |
| MarketOverview | Tool Response | mcp-market-data | mcp-market-data | 1.0 |
| CustomerSegment | Tool Response | mcp-market-data | mcp-market-data | 1.0 |

## Detailed Schemas

### MarketFindings

**Purpose**: Structured market research output written to scratchpad.

```python
class MarketFindings(BaseModel):
    """Market research findings."""
    city: str
    analysis_date: datetime
    
    market_overview: MarketOverviewSummary
    growth_trends: list[GrowthTrend]
    customer_segments: list[CustomerSegmentSummary]
    coffee_culture: CoffeeCultureAnalysis
    
    key_insights: list[str]
    opportunities: list[str]
    challenges: list[str]

class MarketOverviewSummary(BaseModel):
    population: int
    gdp_per_capita: float
    coffee_consumption_per_capita_kg: float
    market_size_eur: float
    cafes_per_capita: float

class GrowthTrend(BaseModel):
    year: int
    market_size: float
    growth_rate: float
    notes: str | None

class CustomerSegmentSummary(BaseModel):
    name: str
    size_percentage: float
    spending_monthly_eur: float
    preferences: list[str]
    visit_frequency: str

class CoffeeCultureAnalysis(BaseModel):
    description: str
    popular_formats: list[str]  # espresso, filter, etc.
    peak_hours: list[str]
    social_vs_functional: str  # ratio description
```

**Example** (written to scratchpad `market_findings` section):
```json
{
  "city": "Vienna",
  "analysis_date": "2025-11-27T10:00:00Z",
  "market_overview": {
    "population": 1900000,
    "gdp_per_capita": 52000,
    "coffee_consumption_per_capita_kg": 8.2,
    "market_size_eur": 450000000,
    "cafes_per_capita": 0.0012
  },
  "customer_segments": [
    {
      "name": "Young Professionals",
      "size_percentage": 25,
      "spending_monthly_eur": 85,
      "preferences": ["specialty coffee", "laptop-friendly", "good wifi"],
      "visit_frequency": "4-5 times per week"
    }
  ],
  "key_insights": [
    "Vienna has strong coffee culture with high per-capita consumption",
    "Growing specialty coffee segment"
  ]
}
```

## Validation Rules

| Field | Rule |
|-------|------|
| population | > 0 |
| size_percentage | 0-100 |
| spending_monthly_eur | >= 0 |
