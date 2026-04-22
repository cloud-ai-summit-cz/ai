"""FastMCP Server for Business Registry - Company and business data tools.

Provides mock data for companies, financials, locations, and industry players
with a focus on coffee shops and cafés for demo purposes.

No session isolation needed - this is read-only reference data.
"""

import logging
from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from models import (
    CompanySummary,
    CompanyProfile,
    CompanyFinancials,
    CompanyLocation,
    IndustryPlayer,
    NewsArticle,
)
from mock_data import (
    search_companies as _search_companies,
    get_company_profile as _get_company_profile,
    get_company_financials as _get_company_financials,
    get_company_locations as _get_company_locations,
    get_industry_players as _get_industry_players,
    get_company_news as _get_company_news,
)

logger = logging.getLogger(__name__)


# Configure authentication
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "business-registry-client",
            "scopes": ["read"],
        }
    }
)

# Create the FastMCP server
mcp = FastMCP(
    name="mcp-business-registry",
    instructions="""
    Business registry and company data tools.
    
    Use these tools to:
    - Search for companies by name, industry, or location
    - Get detailed company profiles and financial information
    - Find company locations and branches
    - Identify top industry players in a region
    - Get recent news about specific companies
    
    Data focuses on coffee shops, cafés, and food & beverage industry
    in major European cities (Vienna, Prague, Munich, etc.).
    """,
    auth=auth,
)


# =============================================================================
# Business Registry Tools
# =============================================================================


@mcp.tool
def search_companies(
    query: str,
    industry: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20,
) -> List[dict]:
    """Search for companies by name, industry, or location.

    Args:
        query: Company name or keyword to search for.
        industry: Industry filter (e.g., 'food_and_beverage', 'coffee_shops').
        location: City or country filter (e.g., 'Vienna', 'Prague').
        max_results: Maximum number of results to return (default: 20).

    Returns:
        List of matching companies with basic information.
    """
    logger.info(f"search_companies | query={query} | industry={industry} | location={location}")
    results = _search_companies(query, industry, location, max_results)
    return [r.model_dump() for r in results]


@mcp.tool
def get_company_profile(company_id: str) -> dict:
    """Get detailed profile of a company.

    Args:
        company_id: Company ID from search results.

    Returns:
        Detailed company information including headquarters, founding year,
        employee count, and ownership type.
    """
    logger.info(f"get_company_profile | company_id={company_id}")
    result = _get_company_profile(company_id)
    if result:
        return result.model_dump()
    return {"error": "Company not found"}


@mcp.tool
def get_company_financials(company_id: str) -> dict:
    """Get financial data for a company.

    Args:
        company_id: Company ID.

    Returns:
        Financial metrics including revenue, margins, and growth rates.
        Note: Many values are estimates based on industry averages.
    """
    logger.info(f"get_company_financials | company_id={company_id}")
    result = _get_company_financials(company_id)
    if result:
        return result.model_dump()
    return {"error": "Financial data not available"}


@mcp.tool
def get_company_locations(
    company_id: str,
    city: Optional[str] = None,
) -> List[dict]:
    """Get all locations/branches of a company.

    Args:
        company_id: Company ID.
        city: Optional city filter to narrow results.

    Returns:
        List of company locations with addresses and details.
    """
    logger.info(f"get_company_locations | company_id={company_id} | city={city}")
    results = _get_company_locations(company_id, city)
    return [r.model_dump() for r in results]


@mcp.tool
def get_industry_players(
    industry: str,
    region: str,
    limit: int = 10,
) -> List[dict]:
    """Get top companies in an industry and region.

    Args:
        industry: Industry (e.g., 'coffee_shops', 'cafes', 'food_service').
        region: City or country (e.g., 'Vienna', 'Prague', 'Munich').
        limit: Number of top players to return (default: 10).

    Returns:
        Ranked list of industry leaders with market share and strengths.
    """
    logger.info(f"get_industry_players | industry={industry} | region={region} | limit={limit}")
    results = _get_industry_players(industry, region, limit)
    return [r.model_dump() for r in results]


@mcp.tool
def get_company_news(
    company_id: str,
    days_back: int = 90,
) -> List[dict]:
    """Get recent news about a specific company.

    Args:
        company_id: Company ID.
        days_back: How many days of news to retrieve (default: 90).

    Returns:
        List of news articles with titles, sources, and sentiment.
    """
    logger.info(f"get_company_news | company_id={company_id} | days_back={days_back}")
    results = _get_company_news(company_id, days_back)
    return [r.model_dump() for r in results]


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-business-registry",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
