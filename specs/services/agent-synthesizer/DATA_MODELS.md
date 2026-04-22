# Service Data Models: agent-synthesizer

Schemas used by the synthesizer agent.

## Schema Inventory

| Name | Type | Owner | Source of Truth | Version |
|------|------|-------|-----------------|---------|
| ExpansionRecommendation | Domain Model | agent-synthesizer | This service | 1.0 |
| SynthesisReport | Output Model | agent-synthesizer | This service | 1.0 |

## Detailed Schemas

### SynthesisReport

**Purpose**: Final synthesized expansion recommendation.

```python
class SynthesisReport(BaseModel):
    """Final synthesis of all research findings."""
    city: str
    report_date: datetime
    
    executive_summary: str
    
    market_summary: str
    competitor_summary: str
    location_summary: str
    financial_summary: str
    
    strengths: list[str]  # Key advantages
    challenges: list[str]  # Key obstacles
    risks: list[RiskAssessment]
    
    recommendation: ExpansionRecommendation
    next_steps: list[str]

class ExpansionRecommendation(BaseModel):
    decision: Literal["proceed", "proceed_with_caution", "delay", "abandon"]
    confidence: float  # 0.0 - 1.0
    rationale: str
    conditions: list[str]  # Conditions for success
    timeline_months: int

class RiskAssessment(BaseModel):
    category: str
    description: str
    likelihood: Literal["low", "medium", "high"]
    impact: Literal["low", "medium", "high"]
    mitigation: str
```

**Example**:
```json
{
  "city": "Vienna",
  "executive_summary": "Vienna presents a strong opportunity for expansion...",
  "recommendation": {
    "decision": "proceed_with_caution",
    "confidence": 0.72,
    "rationale": "Strong market fundamentals but high competition",
    "conditions": [
      "Secure premium location in district 1 or 7",
      "Differentiate with specialty offerings"
    ],
    "timeline_months": 18
  },
  "risks": [
    {
      "category": "Competition",
      "description": "Saturated premium coffee market",
      "likelihood": "high",
      "impact": "medium",
      "mitigation": "Focus on niche positioning"
    }
  ]
}
```
