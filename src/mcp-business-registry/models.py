"""Pydantic models for MCP Business Registry.

Defines data structures for company and business data responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CompanySummary(BaseModel):
    """Summary of a company from search results."""

    company_id: str
    name: str
    industry: str
    location: str
    employees: Optional[int] = None
    founded_year: Optional[int] = None
    description: Optional[str] = None


class CompanyProfile(BaseModel):
    """Detailed company profile."""

    company_id: str
    name: str
    legal_name: str
    industry: str
    sub_industry: Optional[str] = None
    description: str
    headquarters: str
    founded_year: int
    employees: int
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    ceo: Optional[str] = None
    ownership_type: str = "Private"  # Private, Public, Franchise
    parent_company: Optional[str] = None


class CompanyFinancials(BaseModel):
    """Financial data for a company."""

    company_id: str
    currency: str = "EUR"
    annual_revenue: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None  # Year-over-year growth percentage
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    fiscal_year_end: Optional[str] = None
    notes: Optional[str] = None


class CompanyLocation(BaseModel):
    """A physical location of a company."""

    location_id: str
    company_id: str
    name: str
    address: str
    city: str
    country: str
    postal_code: Optional[str] = None
    location_type: str = "Store"  # Store, Office, Warehouse, Factory
    opened_date: Optional[str] = None
    size_sqm: Optional[int] = None
    employees: Optional[int] = None


class IndustryPlayer(BaseModel):
    """A major player in an industry."""

    company_id: str
    name: str
    market_share: Optional[float] = None  # Percentage
    rank: int
    location_count: Optional[int] = None
    strengths: List[str] = Field(default_factory=list)
    founded_year: Optional[int] = None


class NewsArticle(BaseModel):
    """A news article about a company."""

    article_id: str
    company_id: str
    title: str
    source: str
    published_date: str
    summary: str
    url: Optional[str] = None
    sentiment: str = "neutral"  # positive, neutral, negative
