"""Pydantic models for MCP Government Data.

Defines data structures for permits, zoning, regulations, and tax information.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class BusinessPermit(BaseModel):
    """A business permit required for operation."""

    permit_id: str
    name: str
    category: str  # food_service, general_business, health, environment
    description: str
    issuing_authority: str
    estimated_cost: Optional[float] = None
    currency: str = "EUR"
    processing_time_days: Optional[int] = None
    validity_years: Optional[int] = None
    renewal_required: bool = True
    requirements: List[str] = Field(default_factory=list)


class ZoningInfo(BaseModel):
    """Zoning information for a location."""

    zone_code: str
    zone_name: str
    description: str
    permitted_uses: List[str] = Field(default_factory=list)
    prohibited_uses: List[str] = Field(default_factory=list)
    max_building_height_m: Optional[float] = None
    max_floor_area_ratio: Optional[float] = None
    noise_restrictions: Optional[str] = None
    operating_hours_restrictions: Optional[str] = None
    outdoor_seating_allowed: bool = True
    signage_restrictions: Optional[str] = None


class Regulation(BaseModel):
    """An industry-specific regulation."""

    regulation_id: str
    title: str
    category: str  # employment, health, safety, environment
    description: str
    authority: str
    effective_date: Optional[str] = None
    key_requirements: List[str] = Field(default_factory=list)
    penalties_for_violation: Optional[str] = None
    compliance_deadline: Optional[str] = None


class TaxInfo(BaseModel):
    """Business tax information."""

    tax_type: str
    rate: float  # Percentage or fixed amount
    rate_type: str = "percentage"  # percentage, fixed, tiered
    description: str
    filing_frequency: str = "annual"  # monthly, quarterly, annual
    notes: Optional[str] = None


class LicenseRequirement(BaseModel):
    """Professional licensing requirement."""

    license_id: str
    name: str
    profession: str
    description: str
    issuing_authority: str
    requirements: List[str] = Field(default_factory=list)
    training_hours_required: Optional[int] = None
    exam_required: bool = False
    renewal_period_years: Optional[int] = None
    estimated_cost: Optional[float] = None


class HealthSafetyCode(BaseModel):
    """Health and safety code requirement."""

    code_id: str
    title: str
    category: str  # food_safety, fire_safety, workplace_safety, accessibility
    description: str
    key_requirements: List[str] = Field(default_factory=list)
    inspection_frequency: Optional[str] = None
    penalties: Optional[str] = None


class LaborLaw(BaseModel):
    """Employment and labor law information."""

    law_id: str
    topic: str  # minimum_wage, working_hours, benefits, leave, termination
    title: str
    description: str
    key_provisions: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    notes: Optional[str] = None
