"""Pydantic models for MCP Demographics.

Defines data structures for population, income, and consumer behavior data.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PopulationStats(BaseModel):
    """Population statistics for a location."""

    city: str
    district: Optional[str] = None
    total_population: int
    population_density_per_sqkm: float
    growth_rate_yoy: float  # Year-over-year percentage
    median_age: float
    urban_percentage: float = 100.0
    data_year: int = 2024


class IncomeDistribution(BaseModel):
    """Income and purchasing power data."""

    city: str
    district: Optional[str] = None
    median_household_income: float
    mean_household_income: float
    currency: str = "EUR"
    purchasing_power_index: float  # 100 = national average
    income_brackets: Dict[str, float] = Field(default_factory=dict)  # bracket -> percentage
    disposable_income_per_capita: float
    unemployment_rate: float


class AgeDistribution(BaseModel):
    """Age demographics for a location."""

    city: str
    district: Optional[str] = None
    age_groups: Dict[str, float] = Field(default_factory=dict)  # age_range -> percentage
    median_age: float
    dependency_ratio: float  # (0-14 + 65+) / (15-64)
    working_age_percentage: float  # 15-64


class ConsumerSpending(BaseModel):
    """Consumer spending patterns by category."""

    city: str
    category: str
    monthly_average_per_household: float
    currency: str = "EUR"
    yoy_change: float  # Year-over-year percentage change
    share_of_total_spending: float  # Percentage of total consumer spending
    comparison_to_national: float  # Index, 100 = national average
    seasonal_peak: Optional[str] = None  # Month or season
    notes: Optional[str] = None


class LifestyleSegment(BaseModel):
    """Consumer lifestyle segmentation."""

    segment_name: str
    description: str
    percentage_of_population: float
    key_characteristics: List[str] = Field(default_factory=list)
    coffee_consumption_index: float = 100  # 100 = average
    preferred_channels: List[str] = Field(default_factory=list)
    price_sensitivity: str = "medium"  # low, medium, high


class CommuterPattern(BaseModel):
    """Commuter and foot traffic patterns."""

    city: str
    district: Optional[str] = None
    day_type: str  # weekday, weekend
    peak_hours: List[str] = Field(default_factory=list)
    daily_foot_traffic: int  # Estimated daily pedestrians
    commuter_inflow: int  # People commuting INTO the area
    commuter_outflow: int  # People commuting OUT of the area
    public_transit_usage: float  # Percentage using public transit
    main_transit_modes: List[str] = Field(default_factory=list)
    average_commute_time_minutes: int
