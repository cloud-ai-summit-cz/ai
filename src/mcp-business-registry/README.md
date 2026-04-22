# MCP Business Registry

MCP server providing business registry and company data tools.

## Overview

This MCP server provides mock data about companies, particularly focused on the coffee shop and café industry in major European cities (Vienna, Prague, Munich). It's designed for demo purposes with realistic but generated data.

## Tools

| Tool | Description |
|------|-------------|
| `search_companies` | Search for companies by name, industry, or location |
| `get_company_profile` | Get detailed company profile |
| `get_company_financials` | Get financial metrics and data |
| `get_company_locations` | Get all branches/locations of a company |
| `get_industry_players` | Get top players in an industry/region |
| `get_company_news` | Get recent news about a company |

## Mock Data Strategy

The server uses a combination of:
- **Curated data** for well-known cities (Vienna, Prague, Munich) with realistic coffee chains
- **Seeded random generation** for unknown locations, providing consistent but flexible results

This ensures demos work well for typical queries while handling any location gracefully.

## Local Development

```bash
# Install dependencies
uv sync

# Run the server
uv run python main.py

# Or with uvicorn directly
uv run uvicorn main:mcp --host 0.0.0.0 --port 8012
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8012` | Server port |
| `API_KEY` | `dev-business-registry-key` | Authentication key |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Monitor telemetry |

## Docker

```bash
# Build
docker build -t mcp-business-registry .

# Run
docker run -p 8012:8012 -e API_KEY=your-key mcp-business-registry
```
