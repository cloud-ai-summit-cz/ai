# mcp-calculator

MCP server providing financial calculations for business planning - startup costs, operating costs, revenue projections, ROI, cash flow, and sensitivity analysis.

## Tools

| Tool | Description |
|------|-------------|
| `mcp_calculator_startup_costs` | Calculate total startup investment |
| `mcp_calculator_operating_costs` | Calculate monthly/annual operating costs |
| `mcp_calculator_project_revenue` | Project revenue for 3 scenarios over 3 years |
| `mcp_calculator_break_even` | Break-even analysis |
| `mcp_calculator_roi` | ROI, NPV, payback period calculation |
| `mcp_calculator_cash_flow` | Monthly cash flow projections |
| `mcp_calculator_sensitivity` | Sensitivity analysis on key variables |

## Usage Examples

### Startup Costs
```python
result = mcp_calculator_startup_costs(
    rent_monthly=2000,
    size_sqm=90,
    monthly_operating_cost=8000,
    renovation_cost_per_sqm=400,
)
# Returns: total_investment, breakdown, contingency
```

### Break-Even Analysis
```python
result = mcp_calculator_break_even(
    monthly_operating_cost=8000,
    avg_transaction_value=6.5,
    gross_margin_percent=65,
    initial_investment=120000,
)
# Returns: break_even_months, daily_customers_needed
```

## Running Locally

```bash
cd src/mcp-calculator
uv sync
uv run python main.py
```

Server runs on `http://localhost:8005`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_CALCULATOR_API_KEY` | `dev-api-key` | API key for authentication |
| `MCP_CALCULATOR_PORT` | `8005` | Server port |
| `MCP_CALCULATOR_LOG_LEVEL` | `INFO` | Logging level |
