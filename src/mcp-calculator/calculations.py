"""Calculation engine for financial projections.

Pure computation functions - no external dependencies or data.
"""

from models import (
    StartupCostInput,
    StartupCostResult,
    OperatingCostInput,
    OperatingCostResult,
    RevenueInput,
    RevenueProjection,
    BreakEvenResult,
    ROIInput,
    ROIResult,
    CashFlowMonth,
    CashFlowProjection,
    SensitivityScenario,
    SensitivityResult,
)


def calculate_startup_costs(inputs: StartupCostInput) -> StartupCostResult:
    """Calculate total startup investment."""
    breakdown = {
        "lease_deposit": inputs.rent_monthly * inputs.lease_deposit_months,
        "renovation": inputs.size_sqm * inputs.renovation_cost_per_sqm,
        "equipment": inputs.equipment_cost,
        "furniture": inputs.furniture_cost,
        "initial_inventory": inputs.inventory_initial,
        "permits_licenses": inputs.permits_licenses,
        "marketing_launch": inputs.marketing_launch,
        "working_capital": inputs.monthly_operating_cost * inputs.working_capital_months,
    }

    # Add any other costs
    for name, cost in inputs.other_costs.items():
        breakdown[name] = cost

    total = sum(breakdown.values())
    contingency = total * 0.15

    notes = [
        f"Based on {inputs.size_sqm} sqm space at €{inputs.rent_monthly}/month",
        f"Renovation assumes €{inputs.renovation_cost_per_sqm}/sqm fit-out",
        f"Working capital covers {inputs.working_capital_months} months of operations",
        "15% contingency recommended for unexpected costs",
    ]

    return StartupCostResult(
        total_investment=round(total, 2),
        breakdown={k: round(v, 2) for k, v in breakdown.items()},
        contingency_recommended=round(contingency, 2),
        total_with_contingency=round(total + contingency, 2),
        notes=notes,
    )


def calculate_operating_costs(inputs: OperatingCostInput) -> OperatingCostResult:
    """Calculate monthly and annual operating costs."""
    # Staff costs with employer contributions
    staff_cost = inputs.staff_count * inputs.avg_salary_monthly * (1 + inputs.employer_costs_percent / 100)

    breakdown = {
        "rent": inputs.rent_monthly,
        "staff": round(staff_cost, 2),
        "utilities": inputs.utilities_monthly,
        "inventory_supplies": inputs.inventory_monthly,
        "marketing": inputs.marketing_monthly,
        "insurance": inputs.insurance_monthly,
        "maintenance": inputs.maintenance_monthly,
        "software": inputs.software_subscriptions,
    }

    # Add other costs
    for name, cost in inputs.other_monthly.items():
        breakdown[name] = cost

    monthly_total = sum(breakdown.values())

    # Fixed vs variable classification
    fixed_costs = (
        inputs.rent_monthly
        + staff_cost
        + inputs.insurance_monthly
        + inputs.software_subscriptions
        + inputs.maintenance_monthly
    )
    variable_costs = monthly_total - fixed_costs

    return OperatingCostResult(
        monthly_total=round(monthly_total, 2),
        annual_total=round(monthly_total * 12, 2),
        breakdown=breakdown,
        fixed_costs=round(fixed_costs, 2),
        variable_costs=round(variable_costs, 2),
        cost_per_day=round(monthly_total / 26, 2),  # Assuming 26 operating days
    )


def project_revenue(inputs: RevenueInput) -> list[RevenueProjection]:
    """Project revenue for three scenarios over 3 years."""
    scenarios = [
        ("conservative", inputs.daily_customers_low),
        ("expected", inputs.daily_customers_mid),
        ("optimistic", inputs.daily_customers_high),
    ]

    results = []

    for scenario_name, daily_customers in scenarios:
        # Year 1 - monthly base, potentially with ramp-up
        monthly_rev_y1 = daily_customers * inputs.avg_transaction_value * inputs.days_open_per_month
        # Apply average growth across year 1
        avg_multiplier_y1 = 1 + (inputs.growth_rate_year1 * 6)  # Average of 12-month ramp
        annual_y1 = monthly_rev_y1 * 12 * avg_multiplier_y1

        # Year 2
        annual_y2 = annual_y1 * (1 + inputs.growth_rate_year2)

        # Year 3
        annual_y3 = annual_y2 * (1 + inputs.growth_rate_year3)

        results.append(
            RevenueProjection(
                scenario=scenario_name,
                monthly_revenue_year1=round(monthly_rev_y1, 2),
                annual_revenue_year1=round(annual_y1, 2),
                annual_revenue_year2=round(annual_y2, 2),
                annual_revenue_year3=round(annual_y3, 2),
                three_year_total=round(annual_y1 + annual_y2 + annual_y3, 2),
            )
        )

    return results


def calculate_break_even(
    monthly_operating_cost: float,
    avg_transaction_value: float,
    gross_margin_percent: float = 65.0,
    initial_investment: float | None = None,
    days_open_per_month: int = 26,
) -> BreakEvenResult:
    """Calculate break-even point."""
    # Monthly break-even (covering operating costs)
    gross_margin = gross_margin_percent / 100
    monthly_revenue_needed = monthly_operating_cost / gross_margin

    daily_revenue_needed = monthly_revenue_needed / days_open_per_month
    daily_customers_needed = int(daily_revenue_needed / avg_transaction_value) + 1

    # Calculate months to break even on investment
    if initial_investment:
        monthly_profit = monthly_revenue_needed * gross_margin - monthly_operating_cost
        # This is break-even point, profit is 0. Need to solve for profitable scenario
        # For simplicity, assume we need 20% above break-even to pay back investment
        target_monthly_profit = initial_investment / 24  # Target 24-month payback
        actual_revenue_for_payback = (monthly_operating_cost + target_monthly_profit) / gross_margin
        months_to_break_even = int(initial_investment / target_monthly_profit) if target_monthly_profit > 0 else 999
    else:
        months_to_break_even = 0

    assumptions = [
        f"Gross margin: {gross_margin_percent}%",
        f"Average transaction value: €{avg_transaction_value}",
        f"Operating days per month: {days_open_per_month}",
        "Assumes stable operating costs",
    ]

    return BreakEvenResult(
        break_even_months=months_to_break_even,
        break_even_revenue_monthly=round(monthly_revenue_needed, 2),
        daily_customers_needed=daily_customers_needed,
        gross_margin_percent=gross_margin_percent,
        assumptions=assumptions,
    )


def calculate_roi(inputs: ROIInput) -> ROIResult:
    """Calculate return on investment metrics."""
    # Simple ROI
    total_profit = inputs.annual_profit_year1 + inputs.annual_profit_year2 + inputs.annual_profit_year3
    avg_annual_profit = total_profit / 3
    simple_roi = (avg_annual_profit / inputs.total_investment) * 100

    # Payback period
    if inputs.annual_profit_year1 <= 0:
        payback_months = 999
    else:
        cumulative = 0
        month = 0
        monthly_profit_y1 = inputs.annual_profit_year1 / 12
        monthly_profit_y2 = inputs.annual_profit_year2 / 12
        monthly_profit_y3 = inputs.annual_profit_year3 / 12

        while cumulative < inputs.total_investment and month < 36:
            month += 1
            if month <= 12:
                cumulative += monthly_profit_y1
            elif month <= 24:
                cumulative += monthly_profit_y2
            else:
                cumulative += monthly_profit_y3

        payback_months = month if cumulative >= inputs.total_investment else 999

    # NPV calculation
    r = inputs.discount_rate
    npv = (
        -inputs.total_investment
        + inputs.annual_profit_year1 / (1 + r)
        + inputs.annual_profit_year2 / (1 + r) ** 2
        + inputs.annual_profit_year3 / (1 + r) ** 3
    )

    # Rough IRR estimate (simplified)
    if total_profit > inputs.total_investment:
        irr_estimate = (total_profit / inputs.total_investment - 1) / 3  # Simplified
    else:
        irr_estimate = -0.1

    return ROIResult(
        simple_roi_percent=round(simple_roi, 1),
        payback_months=payback_months,
        npv=round(npv, 2),
        irr_estimate=round(irr_estimate * 100, 1),
        three_year_total_profit=round(total_profit, 2),
    )


def project_cash_flow(
    initial_investment: float,
    monthly_operating_cost: float,
    monthly_revenue_year1: float,
    revenue_growth_rate: float = 0.05,
    gross_margin: float = 0.65,
    projection_months: int = 36,
) -> CashFlowProjection:
    """Project month-by-month cash flows."""
    cash_flows = []
    cumulative = -initial_investment

    # Ramp-up in first 6 months
    ramp_up = [0.5, 0.65, 0.75, 0.85, 0.95, 1.0]

    for month in range(1, projection_months + 1):
        # Calculate revenue with ramp-up and growth
        if month <= 6:
            ramp_factor = ramp_up[month - 1]
        else:
            ramp_factor = 1.0

        if month <= 12:
            base_revenue = monthly_revenue_year1
        elif month <= 24:
            base_revenue = monthly_revenue_year1 * (1 + revenue_growth_rate)
        else:
            base_revenue = monthly_revenue_year1 * (1 + revenue_growth_rate) ** 2

        revenue = base_revenue * ramp_factor
        costs = monthly_operating_cost
        net_flow = (revenue * gross_margin) - costs
        cumulative += net_flow

        cash_flows.append(
            CashFlowMonth(
                month=month,
                revenue=round(revenue, 2),
                operating_costs=round(costs, 2),
                net_cash_flow=round(net_flow, 2),
                cumulative_cash_flow=round(cumulative, 2),
            )
        )

    # Find month when cumulative turns positive
    months_to_positive = 999
    for cf in cash_flows:
        if cf.cumulative_cash_flow >= 0:
            months_to_positive = cf.month
            break

    # Summarize by year
    y1_flows = sum(cf.net_cash_flow for cf in cash_flows[:12])
    y2_flows = sum(cf.net_cash_flow for cf in cash_flows[12:24])
    y3_flows = sum(cf.net_cash_flow for cf in cash_flows[24:36])

    return CashFlowProjection(
        projection_months=projection_months,
        initial_investment=initial_investment,
        monthly_cash_flows=cash_flows,
        months_to_positive=months_to_positive,
        year1_net_cash_flow=round(y1_flows, 2),
        year2_net_cash_flow=round(y2_flows, 2),
        year3_net_cash_flow=round(y3_flows, 2),
    )


def sensitivity_analysis(
    monthly_revenue: float,
    monthly_operating_cost: float,
    gross_margin: float = 0.65,
    variables_to_test: list[str] | None = None,
) -> SensitivityResult:
    """Analyze sensitivity of profit to key variables."""
    base_profit = (monthly_revenue * gross_margin) - monthly_operating_cost

    if variables_to_test is None:
        variables_to_test = ["revenue", "rent", "staff_cost", "gross_margin"]

    scenarios = []
    changes = [-20, -10, 10, 20]

    # Revenue sensitivity
    if "revenue" in variables_to_test:
        for change in changes:
            new_revenue = monthly_revenue * (1 + change / 100)
            new_profit = (new_revenue * gross_margin) - monthly_operating_cost
            impact = new_profit - base_profit
            scenarios.append(
                SensitivityScenario(
                    variable="revenue",
                    change_percent=change,
                    new_value=round(new_revenue, 2),
                    impact_on_monthly_profit=round(impact, 2),
                    impact_percent=round((impact / base_profit) * 100 if base_profit != 0 else 0, 1),
                )
            )

    # Rent sensitivity (assuming rent is ~30% of operating cost)
    if "rent" in variables_to_test:
        rent_estimate = monthly_operating_cost * 0.30
        for change in changes:
            cost_delta = rent_estimate * (change / 100)
            new_profit = base_profit - cost_delta
            impact = new_profit - base_profit
            scenarios.append(
                SensitivityScenario(
                    variable="rent",
                    change_percent=change,
                    new_value=round(rent_estimate * (1 + change / 100), 2),
                    impact_on_monthly_profit=round(impact, 2),
                    impact_percent=round((impact / base_profit) * 100 if base_profit != 0 else 0, 1),
                )
            )

    # Staff cost sensitivity (assuming staff is ~40% of operating cost)
    if "staff_cost" in variables_to_test:
        staff_estimate = monthly_operating_cost * 0.40
        for change in changes:
            cost_delta = staff_estimate * (change / 100)
            new_profit = base_profit - cost_delta
            impact = new_profit - base_profit
            scenarios.append(
                SensitivityScenario(
                    variable="staff_cost",
                    change_percent=change,
                    new_value=round(staff_estimate * (1 + change / 100), 2),
                    impact_on_monthly_profit=round(impact, 2),
                    impact_percent=round((impact / base_profit) * 100 if base_profit != 0 else 0, 1),
                )
            )

    # Gross margin sensitivity
    if "gross_margin" in variables_to_test:
        for change in changes:
            new_margin = gross_margin * (1 + change / 100)
            new_profit = (monthly_revenue * new_margin) - monthly_operating_cost
            impact = new_profit - base_profit
            scenarios.append(
                SensitivityScenario(
                    variable="gross_margin",
                    change_percent=change,
                    new_value=round(new_margin * 100, 1),
                    impact_on_monthly_profit=round(impact, 2),
                    impact_percent=round((impact / base_profit) * 100 if base_profit != 0 else 0, 1),
                )
            )

    # Find most sensitive variable
    max_impact = 0
    most_sensitive = "revenue"
    for s in scenarios:
        if abs(s.impact_on_monthly_profit) > max_impact and s.change_percent == 10:
            max_impact = abs(s.impact_on_monthly_profit)
            most_sensitive = s.variable

    recommendation = f"Profit is most sensitive to {most_sensitive}. "
    if most_sensitive == "revenue":
        recommendation += "Focus on customer acquisition and retention."
    elif most_sensitive == "rent":
        recommendation += "Negotiate favorable lease terms."
    elif most_sensitive == "staff_cost":
        recommendation += "Optimize staffing levels and efficiency."
    else:
        recommendation += "Maintain product margins through supplier negotiations."

    return SensitivityResult(
        base_monthly_profit=round(base_profit, 2),
        scenarios=scenarios,
        most_sensitive_variable=most_sensitive,
        recommendation=recommendation,
    )
