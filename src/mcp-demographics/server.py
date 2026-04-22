"""MCP Demographics server using FastMCP.

Provides demographic and consumer behavior data for market analysis.
"""

import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from mock_data import (
    get_population_stats,
    get_income_distribution,
    get_age_distribution,
    get_consumer_spending,
    get_lifestyle_segments,
    get_commuter_patterns,
)

logger = logging.getLogger(__name__)


# Configure authentication
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "demographics-client",
            "scopes": ["read"],
        }
    }
)

# Create MCP server
mcp = FastMCP(
    name="mcp-demographics",
    instructions="""Demographic and consumer behavior data service.

Provides population, income, age distribution, consumer spending,
lifestyle segmentation, and commuter pattern data for location analysis.

Use to understand target markets and consumer characteristics.""",
    auth=auth,
)


# ============================================================================
# Tool Definitions
# ============================================================================


@mcp.tool()
def mcp_demographics_get_population_stats(
    city: str,
    district: str | None = None,
) -> dict:
    """Get population statistics for a city or district.

    Args:
        city: City name (e.g., Vienna, Prague, Munich)
        district: Optional district/neighborhood within the city

    Returns:
        Population count, density, growth rate, and demographic summary
    """
    result = get_population_stats(city=city, district=district)
    return result.model_dump()


@mcp.tool()
def mcp_demographics_get_income_distribution(
    city: str,
    district: str | None = None,
) -> dict:
    """Get income and purchasing power data.

    Args:
        city: City name
        district: Optional district/neighborhood

    Returns:
        Median/mean income, income brackets, purchasing power index, unemployment rate
    """
    result = get_income_distribution(city=city, district=district)
    return result.model_dump()


@mcp.tool()
def mcp_demographics_get_age_distribution(
    city: str,
    district: str | None = None,
) -> dict:
    """Get age demographics for a location.

    Args:
        city: City name
        district: Optional district/neighborhood

    Returns:
        Age group percentages, median age, dependency ratio, working age percentage
    """
    result = get_age_distribution(city=city, district=district)
    return result.model_dump()


@mcp.tool()
def mcp_demographics_get_consumer_spending(
    city: str,
    category: str,
) -> dict:
    """Get consumer spending patterns by category.

    Args:
        city: City name
        category: Spending category (e.g., food_beverage, dining_out, coffee, entertainment, retail)

    Returns:
        Monthly average spending, year-over-year change, share of total, comparison to national average
    """
    result = get_consumer_spending(city=city, category=category)
    return result.model_dump()


@mcp.tool()
def mcp_demographics_get_lifestyle_segments(
    city: str,
    district: str | None = None,
) -> list[dict]:
    """Get consumer lifestyle segmentation analysis.

    Args:
        city: City name
        district: Optional district/neighborhood

    Returns:
        List of lifestyle segments with characteristics, coffee consumption index,
        preferred channels, and price sensitivity
    """
    results = get_lifestyle_segments(city=city, district=district)
    return [r.model_dump() for r in results]


@mcp.tool()
def mcp_demographics_get_commuter_patterns(
    city: str,
    district: str | None = None,
    day_type: str = "weekday",
) -> dict:
    """Get commuter and foot traffic patterns.

    Args:
        city: City name
        district: Optional district/neighborhood
        day_type: Type of day - "weekday", "weekend", or "both"

    Returns:
        Peak hours, daily foot traffic, commuter inflow/outflow,
        public transit usage, main transit modes, average commute time
    """
    result = get_commuter_patterns(city=city, district=district, day_type=day_type)
    return result.model_dump()


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-demographics",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
