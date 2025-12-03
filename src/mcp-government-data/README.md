# MCP Government Data

MCP server providing government permits, zoning, and regulatory data tools.

## Overview

This MCP server provides mock data about business permits, zoning regulations, tax rates, and labor laws for major European countries (Austria, Czech Republic, Germany). It's designed for demo purposes with realistic regulatory information.

## Tools

| Tool | Description |
|------|-------------|
| `get_business_permits` | Get required permits for a business type in a location |
| `get_zoning_info` | Get zoning information for an address or area |
| `get_regulations` | Get industry-specific regulations |
| `get_tax_rates` | Get business tax rates for a location |
| `get_licensing_requirements` | Get professional licensing requirements |
| `get_health_safety_codes` | Get health and safety code requirements |
| `get_labor_laws` | Get employment and labor regulations |

## Mock Data Strategy

The server uses curated data for:
- **Austria (AT)**: Vienna, Salzburg, Graz - Austrian trade law, collective agreements
- **Czech Republic (CZ)**: Prague, Brno - Czech živnostenský system
- **Germany (DE)**: Munich, Berlin, Hamburg - German Gewerbeordnung

This ensures realistic, country-specific regulatory information while remaining flexible for demo queries.

## Local Development

```bash
# Install dependencies
uv sync

# Run the server
uv run python main.py

# Or with uvicorn directly
uv run uvicorn main:mcp --host 0.0.0.0 --port 8013
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8013` | Server port |
| `API_KEY` | `dev-government-data-key` | Authentication key |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Monitor telemetry |

## Docker

```bash
# Build
docker build -t mcp-government-data .

# Run
docker run -p 8013:8013 -e API_KEY=your-key mcp-government-data
```
