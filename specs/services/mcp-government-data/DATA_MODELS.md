# Service Data Models: mcp-government-data

## Tool Response Schemas

```python
class BusinessPermit(BaseModel):
    """Business permit requirement."""
    permit_type: str
    issuing_authority: str
    description: str
    estimated_cost_usd: float
    processing_time_days: int
    renewal_frequency: str
    requirements: list[str]

class ZoningInfo(BaseModel):
    """Zoning information for location."""
    zone_code: str
    zone_name: str
    allowed_uses: list[str]
    restrictions: list[str]
    max_building_height: str | None
    parking_requirements: str | None
    noise_restrictions: str | None

class Regulation(BaseModel):
    """Business regulation."""
    regulation_id: str
    title: str
    category: str
    description: str
    compliance_requirements: list[str]
    penalties: str
    effective_date: datetime

class TaxInfo(BaseModel):
    """Tax information."""
    tax_type: str
    rate_percent: float
    description: str
    filing_frequency: str
    exemptions: list[str]

class LicenseRequirement(BaseModel):
    """Professional license requirement."""
    license_type: str
    required_for: str
    issuing_body: str
    requirements: list[str]
    validity_years: int
    cost_usd: float

class HealthSafetyCode(BaseModel):
    """Health and safety code."""
    code_id: str
    title: str
    requirements: list[str]
    inspection_frequency: str
    violations_penalties: str
```
