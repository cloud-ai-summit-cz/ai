"""Data models for MCP Real Estate server."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CommercialProperty(BaseModel):
    """Commercial property listing."""

    id: str = Field(description="Unique property identifier")
    address: str = Field(description="Street address")
    district: str = Field(description="District/neighborhood")
    city: str = Field(description="City name")
    country: str = Field(description="Country")
    property_type: Literal["retail", "office", "mixed", "restaurant", "cafe"] = Field(
        description="Type of commercial property"
    )
    size_sqm: float = Field(description="Size in square meters")
    monthly_rent_eur: float = Field(description="Monthly rent in EUR")
    price_per_sqm: float = Field(description="Price per square meter per month")
    available_date: str = Field(description="Date when property becomes available")
    features: list[str] = Field(description="Property features and amenities")
    condition: Literal["shell", "basic", "fitted", "turnkey"] = Field(
        description="Property condition/fit-out level"
    )
    lease_term_months: int = Field(description="Minimum lease term in months")
    contact: str = Field(description="Contact information")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class RentalRates(BaseModel):
    """Rental rate data for an area."""

    location: str = Field(description="Location name (city or district)")
    property_type: str = Field(description="Property type")
    avg_rate_sqm_month: float = Field(description="Average rate per sqm per month in EUR")
    min_rate: float = Field(description="Minimum rate in the area")
    max_rate: float = Field(description="Maximum rate in the area")
    trend: Literal["increasing", "stable", "decreasing"] = Field(
        description="Rate trend direction"
    )
    yoy_change_percent: float = Field(description="Year-over-year change percentage")
    currency: str = Field(default="EUR", description="Currency")
    data_quarter: str = Field(description="Data period (e.g., Q1 2024)")


class FootTraffic(BaseModel):
    """Foot traffic data for a location."""

    location: str = Field(description="Location name")
    district: Optional[str] = Field(default=None, description="District if applicable")
    daily_average: int = Field(description="Average daily pedestrians")
    peak_hour: str = Field(description="Peak traffic hour")
    peak_count: int = Field(description="Peak hour pedestrian count")
    weekday_avg: int = Field(description="Average weekday traffic")
    weekend_avg: int = Field(description="Average weekend traffic")
    seasonal_variation: str = Field(description="Seasonal variation notes")
    measurement_source: str = Field(description="Data source")


class NearbyAmenity(BaseModel):
    """Nearby amenity or point of interest."""

    name: str = Field(description="Amenity name")
    type: str = Field(
        description="Type (transit, restaurant, competitor, coworking, university, etc.)"
    )
    distance_meters: int = Field(description="Distance from location in meters")
    relevance: Literal["positive", "neutral", "negative"] = Field(
        description="Relevance for coffee shop (positive=draw, negative=competition)"
    )
    details: Optional[str] = Field(default=None, description="Additional details")


class LocationScore(BaseModel):
    """Composite location scoring for site evaluation."""

    location: str = Field(description="Location name")
    district: Optional[str] = Field(default=None, description="District if applicable")
    overall_score: float = Field(description="Overall location score (0-100)")
    walkability: float = Field(description="Walkability score (0-100)")
    transit_access: float = Field(description="Transit accessibility score (0-100)")
    business_density: float = Field(description="Business density score (0-100)")
    competition_risk: float = Field(description="Competition risk score (0-100, lower=better)")
    growth_potential: float = Field(description="Growth potential score (0-100)")
    coffee_shop_fit: float = Field(description="Coffee shop suitability score (0-100)")
    notes: list[str] = Field(description="Key observations")


class VacancyRate(BaseModel):
    """Commercial vacancy rate data."""

    location: str = Field(description="Location name")
    property_type: str = Field(description="Property type")
    vacancy_rate_percent: float = Field(description="Current vacancy rate percentage")
    trend: Literal["increasing", "stable", "decreasing"] = Field(
        description="Vacancy trend"
    )
    avg_time_to_lease_days: int = Field(description="Average days to lease a property")
    available_units: int = Field(description="Number of available units")
    data_quarter: str = Field(description="Data period")


class LocationComparison(BaseModel):
    """Comparison of multiple locations."""

    locations: list[str] = Field(description="Compared locations")
    best_overall: str = Field(description="Best overall location")
    comparison_factors: dict[str, dict[str, float]] = Field(
        description="Scores by factor by location"
    )
    recommendation: str = Field(description="Recommendation summary")
