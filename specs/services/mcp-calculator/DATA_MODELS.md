# Service Data Models: mcp-calculator

## Tool Input/Output Schemas

```python
class StartupCostInput(BaseModel):
    """Input for startup cost calculation."""
    lease_deposit_months: int = 3
    renovation_cost_sqm: float
    equipment_cost: float
    inventory_initial: float
    permits_licenses: float
    marketing_launch: float
    working_capital_months: int = 3
    monthly_operating_cost: float
    other_costs: dict[str, float] = {}

class StartupCostResult(BaseModel):
    """Startup cost calculation result."""
    total_investment: float
    breakdown: dict[str, float]
    contingency_recommended: float
    total_with_contingency: float

class OperatingCostInput(BaseModel):
    """Input for operating cost calculation."""
    rent_monthly: float
    staff_count: int
    avg_salary: float
    utilities_monthly: float
    inventory_monthly: float
    marketing_monthly: float
    insurance_monthly: float
    other_monthly: dict[str, float] = {}

class OperatingCostResult(BaseModel):
    """Operating cost calculation result."""
    monthly_total: float
    annual_total: float
    breakdown: dict[str, float]
    fixed_costs: float
    variable_costs: float

class BreakEvenResult(BaseModel):
    """Break-even analysis result."""
    break_even_months: int
    break_even_revenue: float
    daily_customers_needed: int
    monthly_revenue_needed: float
    assumptions: list[str]

class ROIResult(BaseModel):
    """ROI calculation result."""
    roi_percent: float
    payback_months: int
    annual_return: float
    five_year_total_return: float

class CashFlowProjection(BaseModel):
    """Cash flow projection."""
    period: str
    revenue: float
    costs: float
    net_cash_flow: float
    cumulative_cash_flow: float

class SensitivityResult(BaseModel):
    """Sensitivity analysis result."""
    variable: str
    base_case: float
    scenarios: list[dict]  # {change_percent, new_value, impact_on_profit}
```
