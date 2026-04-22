# Service Data Models: mcp-real-estate

## Tool Response Schemas

```python
class CommercialProperty(BaseModel):
    """Commercial property listing."""
    id: str
    address: str
    district: str
    city: str
    property_type: str  # retail, office, mixed
    size_sqm: float
    monthly_rent_usd: float
    available_date: datetime
    features: list[str]
    contact: str

class RentalRates(BaseModel):
    """Rental rate data."""
    location: str
    property_type: str
    avg_rate_sqm_month: float
    min_rate: float
    max_rate: float
    trend: Literal["increasing", "stable", "decreasing"]
    yoy_change_percent: float

class FootTraffic(BaseModel):
    """Foot traffic data."""
    location: str
    daily_average: int
    peak_hour: str
    peak_count: int
    weekday_avg: int
    weekend_avg: int
    seasonal_variation: str

class NearbyAmenity(BaseModel):
    """Nearby amenity."""
    name: str
    type: str  # transit, restaurant, competitor, etc.
    distance_meters: int
    relevance: Literal["positive", "neutral", "negative"]

class LocationScore(BaseModel):
    """Location scoring."""
    location: str
    overall_score: float  # 0-100
    walkability: float
    transit_access: float
    business_density: float
    competition_risk: float
    growth_potential: float

class VacancyRate(BaseModel):
    """Vacancy rate data."""
    location: str
    property_type: str
    vacancy_rate_percent: float
    trend: str
    avg_time_to_lease_days: int
```
