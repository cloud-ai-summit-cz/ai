"""MCP Calculator server using FastMCP.

Provides financial calculations for business planning:
startup costs, operating costs, revenue projections, ROI, and sensitivity analysis.
"""

import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from models import (
    StartupCostInput,
    OperatingCostInput,
    RevenueInput,
    ROIInput,
)
from calculations import (
    calculate_startup_costs,
    calculate_operating_costs,
    project_revenue,
    calculate_break_even,
    calculate_roi,
    project_cash_flow,
    sensitivity_analysis,
)

logger = logging.getLogger(__name__)


# Configure authentication
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "calculator-client",
            "scopes": ["read"],
        }
    }
)

# Create MCP server
mcp = FastMCP(
    name="mcp-calculator",
    instructions="""Financial calculation service for business planning.

Provides pure computation tools for:
- Startup cost estimation
- Operating cost analysis
- Revenue projections
- Break-even analysis
- ROI calculation
- Cash flow projections
- Sensitivity analysis

Use for coffee shop expansion financial modeling.""",
    auth=auth,
)


# ============================================================================
# Tool Definitions
# ============================================================================


@mcp.tool()
def mcp_calculator_startup_costs(
    rent_monthly: float,
    size_sqm: float,
    monthly_operating_cost: float,
    lease_deposit_months: int = 3,
    renovation_cost_per_sqm: float = 500,
    equipment_cost: float = 25000,
    furniture_cost: float = 15000,
    inventory_initial: float = 5000,
    permits_licenses: float = 2000,
    marketing_launch: float = 5000,
    working_capital_months: int = 3,
    other_costs: dict[str, float] | None = None,
) -> dict:
    """Calculate total startup investment for a new location.

    Args:
        rent_monthly: Monthly rent in EUR
        size_sqm: Space size in square meters
        monthly_operating_cost: Estimated monthly operating cost
        lease_deposit_months: Number of months for lease deposit (default 3)
        renovation_cost_per_sqm: Renovation/fit-out cost per sqm (default €500)
        equipment_cost: Coffee equipment cost (default €25,000)
        furniture_cost: Furniture and fixtures (default €15,000)
        inventory_initial: Initial inventory cost (default €5,000)
        permits_licenses: Permits and license fees (default €2,000)
        marketing_launch: Launch marketing budget (default €5,000)
        working_capital_months: Months of working capital reserve (default 3)
        other_costs: Additional one-time costs as dict

    Returns:
        Total investment, breakdown by category, recommended contingency
    """
    inputs = StartupCostInput(
        rent_monthly=rent_monthly,
        lease_deposit_months=lease_deposit_months,
        size_sqm=size_sqm,
        renovation_cost_per_sqm=renovation_cost_per_sqm,
        equipment_cost=equipment_cost,
        furniture_cost=furniture_cost,
        inventory_initial=inventory_initial,
        permits_licenses=permits_licenses,
        marketing_launch=marketing_launch,
        working_capital_months=working_capital_months,
        monthly_operating_cost=monthly_operating_cost,
        other_costs=other_costs or {},
    )
    result = calculate_startup_costs(inputs)
    return result.model_dump()


@mcp.tool()
def mcp_calculator_operating_costs(
    rent_monthly: float,
    staff_count: int,
    avg_salary_monthly: float,
    employer_costs_percent: float = 35,
    utilities_monthly: float = 500,
    inventory_monthly: float = 4000,
    marketing_monthly: float = 800,
    insurance_monthly: float = 200,
    maintenance_monthly: float = 300,
    software_subscriptions: float = 150,
    other_monthly: dict[str, float] | None = None,
) -> dict:
    """Calculate monthly and annual operating costs.

    Args:
        rent_monthly: Monthly rent in EUR
        staff_count: Number of staff members
        avg_salary_monthly: Average monthly salary per staff member
        employer_costs_percent: Employer social costs percentage (default 35%)
        utilities_monthly: Monthly utilities (default €500)
        inventory_monthly: Monthly inventory/supplies (default €4,000)
        marketing_monthly: Monthly marketing spend (default €800)
        insurance_monthly: Monthly insurance (default €200)
        maintenance_monthly: Monthly maintenance (default €300)
        software_subscriptions: Monthly software costs (default €150)
        other_monthly: Other monthly costs as dict

    Returns:
        Monthly total, annual total, breakdown, fixed vs variable costs
    """
    inputs = OperatingCostInput(
        rent_monthly=rent_monthly,
        staff_count=staff_count,
        avg_salary_monthly=avg_salary_monthly,
        employer_costs_percent=employer_costs_percent,
        utilities_monthly=utilities_monthly,
        inventory_monthly=inventory_monthly,
        marketing_monthly=marketing_monthly,
        insurance_monthly=insurance_monthly,
        maintenance_monthly=maintenance_monthly,
        software_subscriptions=software_subscriptions,
        other_monthly=other_monthly or {},
    )
    result = calculate_operating_costs(inputs)
    return result.model_dump()


@mcp.tool()
def mcp_calculator_project_revenue(
    daily_customers_low: int,
    daily_customers_mid: int,
    daily_customers_high: int,
    avg_transaction_value: float = 6.5,
    days_open_per_month: int = 26,
    growth_rate_year1: float = 0.0,
    growth_rate_year2: float = 0.05,
    growth_rate_year3: float = 0.03,
) -> list[dict]:
    """Project revenue for three scenarios over 3 years.

    Args:
        daily_customers_low: Daily customers - conservative estimate
        daily_customers_mid: Daily customers - expected
        daily_customers_high: Daily customers - optimistic
        avg_transaction_value: Average transaction value in EUR (default €6.50)
        days_open_per_month: Operating days per month (default 26)
        growth_rate_year1: Monthly growth rate in year 1 (default 0)
        growth_rate_year2: Annual growth rate year 2 (default 5%)
        growth_rate_year3: Annual growth rate year 3 (default 3%)

    Returns:
        Three scenarios (conservative, expected, optimistic) with annual revenues
    """
    inputs = RevenueInput(
        avg_transaction_value=avg_transaction_value,
        daily_customers_low=daily_customers_low,
        daily_customers_mid=daily_customers_mid,
        daily_customers_high=daily_customers_high,
        days_open_per_month=days_open_per_month,
        growth_rate_year1=growth_rate_year1,
        growth_rate_year2=growth_rate_year2,
        growth_rate_year3=growth_rate_year3,
    )
    results = project_revenue(inputs)
    return [r.model_dump() for r in results]


@mcp.tool()
def mcp_calculator_break_even(
    monthly_operating_cost: float,
    avg_transaction_value: float = 6.5,
    gross_margin_percent: float = 65.0,
    initial_investment: float | None = None,
    days_open_per_month: int = 26,
) -> dict:
    """Calculate break-even point.

    Args:
        monthly_operating_cost: Total monthly operating cost
        avg_transaction_value: Average transaction value (default €6.50)
        gross_margin_percent: Gross margin percentage (default 65%)
        initial_investment: Optional total startup investment
        days_open_per_month: Operating days per month (default 26)

    Returns:
        Break-even revenue, customers needed per day, months to break even
    """
    result = calculate_break_even(
        monthly_operating_cost=monthly_operating_cost,
        avg_transaction_value=avg_transaction_value,
        gross_margin_percent=gross_margin_percent,
        initial_investment=initial_investment,
        days_open_per_month=days_open_per_month,
    )
    return result.model_dump()


@mcp.tool()
def mcp_calculator_roi(
    total_investment: float,
    annual_profit_year1: float,
    annual_profit_year2: float,
    annual_profit_year3: float,
    discount_rate: float = 0.10,
) -> dict:
    """Calculate return on investment metrics.

    Args:
        total_investment: Total startup investment
        annual_profit_year1: Expected annual profit year 1
        annual_profit_year2: Expected annual profit year 2
        annual_profit_year3: Expected annual profit year 3
        discount_rate: Discount rate for NPV calculation (default 10%)

    Returns:
        Simple ROI, payback period, NPV, estimated IRR
    """
    inputs = ROIInput(
        total_investment=total_investment,
        annual_profit_year1=annual_profit_year1,
        annual_profit_year2=annual_profit_year2,
        annual_profit_year3=annual_profit_year3,
        discount_rate=discount_rate,
    )
    result = calculate_roi(inputs)
    return result.model_dump()


@mcp.tool()
def mcp_calculator_cash_flow(
    initial_investment: float,
    monthly_operating_cost: float,
    monthly_revenue_year1: float,
    revenue_growth_rate: float = 0.05,
    gross_margin: float = 0.65,
    projection_months: int = 36,
) -> dict:
    """Project month-by-month cash flows.

    Args:
        initial_investment: Total startup investment
        monthly_operating_cost: Monthly operating cost
        monthly_revenue_year1: Expected monthly revenue in year 1
        revenue_growth_rate: Annual revenue growth rate (default 5%)
        gross_margin: Gross margin ratio (default 0.65)
        projection_months: Number of months to project (default 36)

    Returns:
        Monthly cash flows, cumulative position, months to positive cash flow
    """
    result = project_cash_flow(
        initial_investment=initial_investment,
        monthly_operating_cost=monthly_operating_cost,
        monthly_revenue_year1=monthly_revenue_year1,
        revenue_growth_rate=revenue_growth_rate,
        gross_margin=gross_margin,
        projection_months=projection_months,
    )
    return result.model_dump()


@mcp.tool()
def mcp_calculator_sensitivity(
    monthly_revenue: float,
    monthly_operating_cost: float,
    gross_margin: float = 0.65,
    variables_to_test: list[str] | None = None,
) -> dict:
    """Analyze sensitivity of profit to key variables.

    Args:
        monthly_revenue: Base monthly revenue
        monthly_operating_cost: Base monthly operating cost
        gross_margin: Gross margin ratio (default 0.65)
        variables_to_test: Variables to test (default: revenue, rent, staff_cost, gross_margin)

    Returns:
        Impact of +/- 10% and 20% changes on each variable, most sensitive factor
    """
    result = sensitivity_analysis(
        monthly_revenue=monthly_revenue,
        monthly_operating_cost=monthly_operating_cost,
        gross_margin=gross_margin,
        variables_to_test=variables_to_test,
    )
    return result.model_dump()


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-calculator",
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
