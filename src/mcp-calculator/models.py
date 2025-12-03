"""Data models for MCP Calculator server."""

from typing import Optional

from pydantic import BaseModel, Field


class StartupCostInput(BaseModel):
    """Input for startup cost calculation."""

    rent_monthly: float = Field(description="Monthly rent in EUR")
    lease_deposit_months: int = Field(default=3, description="Number of months for lease deposit")
    size_sqm: float = Field(description="Space size in square meters")
    renovation_cost_per_sqm: float = Field(default=500, description="Renovation cost per sqm")
    equipment_cost: float = Field(default=25000, description="Coffee equipment (espresso machine, grinders, etc.)")
    furniture_cost: float = Field(default=15000, description="Furniture and fixtures")
    inventory_initial: float = Field(default=5000, description="Initial inventory (coffee, supplies)")
    permits_licenses: float = Field(default=2000, description="Permits and license fees")
    marketing_launch: float = Field(default=5000, description="Launch marketing budget")
    working_capital_months: int = Field(default=3, description="Months of working capital reserve")
    monthly_operating_cost: float = Field(description="Estimated monthly operating cost")
    other_costs: dict[str, float] = Field(default_factory=dict, description="Additional one-time costs")


class StartupCostResult(BaseModel):
    """Startup cost calculation result."""

    total_investment: float = Field(description="Total investment required")
    breakdown: dict[str, float] = Field(description="Cost breakdown by category")
    contingency_recommended: float = Field(description="Recommended contingency (15%)")
    total_with_contingency: float = Field(description="Total including contingency")
    notes: list[str] = Field(description="Calculation notes and assumptions")


class OperatingCostInput(BaseModel):
    """Input for operating cost calculation."""

    rent_monthly: float = Field(description="Monthly rent in EUR")
    staff_count: int = Field(description="Number of staff members")
    avg_salary_monthly: float = Field(description="Average monthly salary per staff")
    employer_costs_percent: float = Field(default=35, description="Employer social costs percentage")
    utilities_monthly: float = Field(default=500, description="Utilities (electricity, water, gas)")
    inventory_monthly: float = Field(default=4000, description="Monthly inventory/supplies")
    marketing_monthly: float = Field(default=800, description="Monthly marketing spend")
    insurance_monthly: float = Field(default=200, description="Monthly insurance")
    maintenance_monthly: float = Field(default=300, description="Monthly maintenance/repairs")
    software_subscriptions: float = Field(default=150, description="POS, accounting software, etc.")
    other_monthly: dict[str, float] = Field(default_factory=dict, description="Other monthly costs")


class OperatingCostResult(BaseModel):
    """Operating cost calculation result."""

    monthly_total: float = Field(description="Total monthly operating cost")
    annual_total: float = Field(description="Annual operating cost")
    breakdown: dict[str, float] = Field(description="Monthly cost breakdown")
    fixed_costs: float = Field(description="Fixed monthly costs")
    variable_costs: float = Field(description="Variable monthly costs")
    cost_per_day: float = Field(description="Daily operating cost")


class RevenueInput(BaseModel):
    """Input for revenue projection."""

    avg_transaction_value: float = Field(default=6.5, description="Average transaction value in EUR")
    daily_customers_low: int = Field(description="Daily customers - conservative estimate")
    daily_customers_mid: int = Field(description="Daily customers - expected")
    daily_customers_high: int = Field(description="Daily customers - optimistic")
    days_open_per_month: int = Field(default=26, description="Operating days per month")
    growth_rate_year1: float = Field(default=0.0, description="Monthly growth rate in year 1")
    growth_rate_year2: float = Field(default=0.05, description="Annual growth rate year 2")
    growth_rate_year3: float = Field(default=0.03, description="Annual growth rate year 3")


class RevenueProjection(BaseModel):
    """Revenue projection result."""

    scenario: str = Field(description="Scenario name (conservative, expected, optimistic)")
    monthly_revenue_year1: float
    annual_revenue_year1: float
    annual_revenue_year2: float
    annual_revenue_year3: float
    three_year_total: float


class BreakEvenResult(BaseModel):
    """Break-even analysis result."""

    break_even_months: int = Field(description="Months to break even")
    break_even_revenue_monthly: float = Field(description="Monthly revenue needed to cover costs")
    daily_customers_needed: int = Field(description="Daily customers needed for break-even")
    gross_margin_percent: float = Field(description="Assumed gross margin")
    assumptions: list[str] = Field(description="Key assumptions")


class ROIInput(BaseModel):
    """Input for ROI calculation."""

    total_investment: float = Field(description="Total startup investment")
    annual_profit_year1: float = Field(description="Expected annual profit year 1")
    annual_profit_year2: float = Field(description="Expected annual profit year 2")
    annual_profit_year3: float = Field(description="Expected annual profit year 3")
    discount_rate: float = Field(default=0.10, description="Discount rate for NPV")


class ROIResult(BaseModel):
    """ROI calculation result."""

    simple_roi_percent: float = Field(description="Simple ROI (3-year average profit / investment)")
    payback_months: int = Field(description="Payback period in months")
    npv: float = Field(description="Net Present Value")
    irr_estimate: float = Field(description="Estimated IRR")
    three_year_total_profit: float = Field(description="Total profit over 3 years")


class CashFlowMonth(BaseModel):
    """Monthly cash flow entry."""

    month: int
    revenue: float
    operating_costs: float
    net_cash_flow: float
    cumulative_cash_flow: float


class CashFlowProjection(BaseModel):
    """Cash flow projection result."""

    projection_months: int
    initial_investment: float
    monthly_cash_flows: list[CashFlowMonth]
    months_to_positive: int = Field(description="Months until cumulative cash flow turns positive")
    year1_net_cash_flow: float
    year2_net_cash_flow: float
    year3_net_cash_flow: float


class SensitivityScenario(BaseModel):
    """Single sensitivity scenario."""

    variable: str
    change_percent: float
    new_value: float
    impact_on_monthly_profit: float
    impact_percent: float


class SensitivityResult(BaseModel):
    """Sensitivity analysis result."""

    base_monthly_profit: float
    scenarios: list[SensitivityScenario]
    most_sensitive_variable: str
    recommendation: str
