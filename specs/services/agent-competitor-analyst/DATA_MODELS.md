# Service Data Models: agent-competitor-analyst

Schemas used by the competitor-analyst agent.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| CompetitorAnalysis | Domain Model | agent-competitor-analyst | This service | 1.0 |
| CompetitorProfile | Tool Response | mcp-competitor | mcp-competitor | 1.0 |

## Detailed Schemas

### CompetitorAnalysis

**Purpose**: Structured competitor analysis output.

```python
class CompetitorAnalysis(BaseModel):
    """Competitor analysis findings."""
    city: str
    analysis_date: datetime
    
    competitors: list[CompetitorAssessment]
    market_concentration: str  # fragmented, moderate, concentrated
    competitive_intensity: Literal["low", "medium", "high"]
    
    opportunities: list[str]
    threats: list[str]
    differentiation_strategies: list[str]

class CompetitorAssessment(BaseModel):
    name: str
    type: str  # chain, independent, specialty
    locations_count: int
    market_share_estimate: float
    positioning: str
    price_tier: Literal["budget", "mid-range", "premium"]
    strengths: list[str]
    weaknesses: list[str]
    threat_level: Literal["low", "medium", "high"]
```

**Example**:
```json
{
  "city": "Vienna",
  "competitors": [
    {
      "name": "Starbucks",
      "type": "chain",
      "locations_count": 15,
      "market_share_estimate": 8.5,
      "positioning": "Global premium coffee chain",
      "price_tier": "premium",
      "strengths": ["Brand recognition", "Consistency"],
      "weaknesses": ["Perceived as not authentic"],
      "threat_level": "medium"
    }
  ],
  "competitive_intensity": "high",
  "differentiation_strategies": [
    "Focus on local/authentic positioning",
    "Specialty single-origin offerings"
  ]
}
```
