"""MCP Real Estate server using FastMCP.

Provides commercial property listings, rental rates, foot traffic,
and location analysis for expansion planning.
"""

import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from mock_data import (
    search_commercial_properties,
    get_rental_rates,
    get_foot_traffic,
    get_nearby_amenities,
    get_location_score,
    get_vacancy_rates,
    compare_locations,
)

logger = logging.getLogger(__name__)


# Configure authentication
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "realestate-client",
            "scopes": ["read"],
        }
    }
)

# Create MCP server
mcp = FastMCP(
    name="mcp-real-estate",
    instructions="""Commercial real estate and location analysis service.

Provides property listings, rental rates, foot traffic data, and location
scoring for site selection decisions. Focused on retail/café-suitable
commercial spaces in Central European cities.

Use to evaluate potential locations for coffee shop expansion.""",
    auth=auth,
)


# ============================================================================
# Tool Definitions
# ============================================================================


@mcp.tool()
def mcp_realestate_search_properties(
    city: str,
    district: str | None = None,
    property_type: str | None = None,
    min_size_sqm: float | None = None,
    max_size_sqm: float | None = None,
    max_rent_eur: float | None = None,
) -> list[dict]:
    """Search for available commercial properties.

    Args:
        city: City to search in (e.g., Brno, Vienna, Prague)
        district: Optional district/neighborhood filter
        property_type: Type filter (retail, cafe, office, mixed)
        min_size_sqm: Minimum size in square meters
        max_size_sqm: Maximum size in square meters
        max_rent_eur: Maximum monthly rent in EUR

    Returns:
        List of matching commercial property listings with address, size,
        rent, features, condition, and availability
    """
    results = search_commercial_properties(
        city=city,
        district=district,
        property_type=property_type,
        min_size_sqm=min_size_sqm,
        max_size_sqm=max_size_sqm,
        max_rent_eur=max_rent_eur,
    )
    return [r.model_dump() for r in results]


@mcp.tool()
def mcp_realestate_get_rental_rates(
    city: str,
    district: str | None = None,
    property_type: str = "retail",
) -> dict:
    """Get rental rate data for an area.

    Args:
        city: City name
        district: Optional district for more specific rates
        property_type: Property type (retail, cafe, office)

    Returns:
        Average, min, max rental rates per sqm/month, trends, and YoY change
    """
    result = get_rental_rates(city=city, district=district, property_type=property_type)
    return result.model_dump()


@mcp.tool()
def mcp_realestate_get_foot_traffic(
    city: str,
    district: str | None = None,
) -> dict:
    """Get pedestrian foot traffic data for a location.

    Args:
        city: City name
        district: Optional district for location-specific data

    Returns:
        Daily average, peak hours, weekday/weekend patterns, seasonal notes
    """
    result = get_foot_traffic(city=city, district=district)
    return result.model_dump()


@mcp.tool()
def mcp_realestate_get_nearby_amenities(
    city: str,
    district: str,
    radius_meters: int = 500,
) -> list[dict]:
    """Get nearby amenities and points of interest.

    Args:
        city: City name
        district: District/neighborhood
        radius_meters: Search radius (default 500m)

    Returns:
        List of nearby amenities with type, distance, and relevance
        (positive=customer draw, negative=competitor)
    """
    results = get_nearby_amenities(city=city, district=district, radius_meters=radius_meters)
    return [r.model_dump() for r in results]


@mcp.tool()
def mcp_realestate_get_location_score(
    city: str,
    district: str,
) -> dict:
    """Get composite location score for site evaluation.

    Args:
        city: City name
        district: District/neighborhood to evaluate

    Returns:
        Overall score (0-100), component scores (walkability, transit,
        business density, competition risk, growth potential, coffee shop fit),
        and key observations
    """
    result = get_location_score(city=city, district=district)
    return result.model_dump()


@mcp.tool()
def mcp_realestate_get_vacancy_rates(
    city: str,
    property_type: str = "retail",
) -> dict:
    """Get commercial property vacancy rate data.

    Args:
        city: City name
        property_type: Property type (retail, cafe)

    Returns:
        Vacancy rate percentage, trend, average time to lease, available units
    """
    result = get_vacancy_rates(city=city, property_type=property_type)
    return result.model_dump()


@mcp.tool()
def mcp_realestate_compare_locations(
    locations: list[dict],
) -> dict:
    """Compare multiple locations for site selection.

    Args:
        locations: List of locations to compare, each with 'city' and 'district' keys
                  Example: [{"city": "Brno", "district": "Veveří"}, {"city": "Vienna", "district": "Neubau"}]

    Returns:
        Comparison across factors, best overall location, and recommendation
    """
    result = compare_locations(locations=locations)
    return result.model_dump()


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-real-estate",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
