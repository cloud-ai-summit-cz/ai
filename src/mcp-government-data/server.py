"""FastMCP Server for Government Data - Permits, zoning, and regulatory data.

Provides mock data for business permits, zoning regulations, tax rates,
and labor laws with a focus on European countries for demo purposes.

No session isolation needed - this is read-only reference data.
"""

import logging
from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from mock_data import (
    get_business_permits as _get_business_permits,
    get_zoning_info as _get_zoning_info,
    get_regulations as _get_regulations,
    get_tax_rates as _get_tax_rates,
    get_licensing_requirements as _get_licensing_requirements,
    get_health_safety_codes as _get_health_safety_codes,
    get_labor_laws as _get_labor_laws,
)

logger = logging.getLogger(__name__)


# Configure authentication
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "government-data-client",
            "scopes": ["read"],
        }
    }
)

# Create the FastMCP server
mcp = FastMCP(
    name="mcp-government-data",
    instructions="""
    Government permits, zoning, and regulatory data tools.
    
    Use these tools to:
    - Find required business permits for a location
    - Check zoning restrictions and permitted uses
    - Get tax rates and filing requirements
    - Understand labor laws and employment regulations
    - Find licensing requirements for professions
    - Review health and safety code requirements
    
    Data covers Austria, Czech Republic, and Germany with realistic
    regulatory information for coffee shops, cafés, and food service.
    """,
    auth=auth,
)


# =============================================================================
# Government Data Tools
# =============================================================================


@mcp.tool
def get_business_permits(
    city: str,
    business_type: str,
    country: Optional[str] = None,
) -> List[dict]:
    """Get required permits for a business type in a location.

    Args:
        city: City name (e.g., 'Vienna', 'Prague', 'Munich').
        business_type: Type of business (e.g., 'coffee_shop', 'restaurant', 'cafe').
        country: Optional country code or name (e.g., 'AT', 'Austria').

    Returns:
        List of required permits with costs, processing times, and requirements.
    """
    logger.info(f"get_business_permits | city={city} | business_type={business_type} | country={country}")
    results = _get_business_permits(city, business_type, country)
    return [r.model_dump() for r in results]


@mcp.tool
def get_zoning_info(
    city: str,
    district: Optional[str] = None,
    address: Optional[str] = None,
) -> dict:
    """Get zoning information for a specific address or area.

    Args:
        city: City name.
        district: District or neighborhood (optional).
        address: Specific street address (optional).

    Returns:
        Zoning details including permitted uses, restrictions, and requirements.
    """
    logger.info(f"get_zoning_info | city={city} | district={district} | address={address}")
    result = _get_zoning_info(city, district, address)
    return result.model_dump()


@mcp.tool
def get_regulations(
    country: str,
    industry: str,
    category: Optional[str] = None,
) -> List[dict]:
    """Get industry-specific regulations.

    Args:
        country: Country name or code (e.g., 'Austria', 'AT').
        industry: Industry (e.g., 'food_service', 'coffee_shops', 'retail').
        category: Filter by category: 'employment', 'health', 'safety', 'environment', or 'all'.

    Returns:
        List of applicable regulations with key requirements.
    """
    logger.info(f"get_regulations | country={country} | industry={industry} | category={category}")
    results = _get_regulations(country, industry, category)
    return [r.model_dump() for r in results]


@mcp.tool
def get_tax_rates(
    country: str,
    city: Optional[str] = None,
    business_type: Optional[str] = None,
) -> List[dict]:
    """Get business tax rates for a location.

    Args:
        country: Country name or code.
        city: City for local tax rates (optional).
        business_type: Type of business for specific rates (optional).

    Returns:
        List of applicable taxes with rates and filing frequencies.
    """
    logger.info(f"get_tax_rates | country={country} | city={city} | business_type={business_type}")
    results = _get_tax_rates(country, city, business_type)
    return [r.model_dump() for r in results]


@mcp.tool
def get_licensing_requirements(
    country: str,
    profession: str,
) -> List[dict]:
    """Get professional licensing requirements.

    Args:
        country: Country name or code.
        profession: Profession type (e.g., 'food_handler', 'barista', 'chef').

    Returns:
        List of required and recommended certifications with training requirements.
    """
    logger.info(f"get_licensing_requirements | country={country} | profession={profession}")
    results = _get_licensing_requirements(country, profession)
    return [r.model_dump() for r in results]


@mcp.tool
def get_health_safety_codes(
    country: str,
    establishment_type: str,
) -> List[dict]:
    """Get health and safety codes for food service establishments.

    Args:
        country: Country name or code.
        establishment_type: Type of establishment (e.g., 'cafe', 'restaurant', 'bakery').

    Returns:
        List of health and safety requirements with inspection frequencies.
    """
    logger.info(f"get_health_safety_codes | country={country} | establishment_type={establishment_type}")
    results = _get_health_safety_codes(country, establishment_type)
    return [r.model_dump() for r in results]


@mcp.tool
def get_labor_laws(
    country: str,
    topics: Optional[List[str]] = None,
) -> List[dict]:
    """Get employment and labor regulations.

    Args:
        country: Country name or code.
        topics: Filter by topics: 'minimum_wage', 'working_hours', 'benefits', 'leave'.
                If None, returns all labor laws.

    Returns:
        List of labor laws with key provisions and requirements.
    """
    logger.info(f"get_labor_laws | country={country} | topics={topics}")
    results = _get_labor_laws(country, topics)
    return [r.model_dump() for r in results]


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-government-data",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
