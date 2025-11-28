# Service Data Models: mcp-demographics

## Tool Response Schemas

```python
class PopulationStats(BaseModel):
    """Population statistics."""
    location: str
    total_population: int
    population_density_sqkm: float
    growth_rate_percent: float
    urban_percent: float
    households: int
    avg_household_size: float

class IncomeDistribution(BaseModel):
    """Income distribution data."""
    location: str
    median_income_usd: float
    mean_income_usd: float
    brackets: list[IncomeBracket]
    purchasing_power_index: float

class IncomeBracket(BaseModel):
    """Income bracket."""
    range_label: str  # e.g., "$50k-$75k"
    min_usd: float
    max_usd: float
    percent_population: float

class AgeDistribution(BaseModel):
    """Age demographics."""
    location: str
    median_age: float
    brackets: list[AgeBracket]

class AgeBracket(BaseModel):
    """Age bracket."""
    range_label: str  # e.g., "25-34"
    percent_population: float

class ConsumerSpending(BaseModel):
    """Consumer spending patterns."""
    location: str
    category: str
    monthly_avg_usd: float
    growth_trend: Literal["increasing", "stable", "decreasing"]
    seasonality: str | None

class LifestyleSegment(BaseModel):
    """Consumer lifestyle segment."""
    segment_name: str
    description: str
    percent_population: float
    characteristics: list[str]
    spending_priorities: list[str]

class CommuterPattern(BaseModel):
    """Commuter and traffic pattern."""
    location: str
    peak_hours: list[str]
    daily_footfall: int
    public_transit_percent: float
    work_from_home_percent: float
```
