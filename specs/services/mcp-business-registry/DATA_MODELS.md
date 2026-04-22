# Service Data Models: mcp-business-registry

## Tool Response Schemas

```python
class CompanySearchResult(BaseModel):
    """Company search result."""
    id: str
    name: str
    industry: str
    location: str
    employee_range: str
    founded: int | None

class CompanyProfile(BaseModel):
    """Detailed company profile."""
    id: str
    name: str
    legal_name: str
    industry: str
    sub_industry: str
    description: str
    founded: int
    headquarters: str
    website: str
    employee_count: int
    ownership_type: Literal["private", "public", "subsidiary", "franchise"]
    parent_company: str | None = None

class CompanyFinancials(BaseModel):
    """Company financial data."""
    company_id: str
    revenue_usd: float | None
    revenue_growth_yoy: float | None
    employee_count: int
    employee_growth_yoy: float | None
    funding_total_usd: float | None
    last_funding_date: datetime | None
    estimated_valuation: float | None

class CompanyLocation(BaseModel):
    """Company location/branch."""
    address: str
    city: str
    country: str
    is_headquarters: bool
    opened_date: datetime | None

class IndustryPlayer(BaseModel):
    """Top player in industry."""
    company_id: str
    name: str
    market_share_percent: float | None
    locations_count: int
    ranking: int
```
