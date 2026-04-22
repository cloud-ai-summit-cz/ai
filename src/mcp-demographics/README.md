# MCP Demographics

MCP server providing demographic and consumer behavior data for market analysis.

## Overview

This service provides demographic information including:
- **Population Statistics**: Population counts, density, growth rates
- **Income Distribution**: Household income, purchasing power, unemployment
- **Age Distribution**: Age demographics, dependency ratios
- **Consumer Spending**: Spending patterns by category
- **Lifestyle Segments**: Consumer segmentation for targeting
- **Commuter Patterns**: Foot traffic and commute data

## Tools

| Tool | Description |
|------|-------------|
| `mcp_demographics_get_population_stats` | Population count, density, growth rate |
| `mcp_demographics_get_income_distribution` | Income levels, purchasing power, unemployment |
| `mcp_demographics_get_age_distribution` | Age group percentages, dependency ratio |
| `mcp_demographics_get_consumer_spending` | Spending by category |
| `mcp_demographics_get_lifestyle_segments` | Consumer segmentation analysis |
| `mcp_demographics_get_commuter_patterns` | Foot traffic and commute patterns |

## Running Locally

```bash
cd src/mcp-demographics
uv sync
uv run python main.py
```

Server starts on `http://localhost:8014`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8014` | Server port |
| `API_KEY` | `dev-demographics-key` | API key for authentication |
| `DEBUG` | `false` | Enable debug logging |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | - | Azure Monitor telemetry |

## Mock Data

The service uses curated data for major cities (Vienna, Prague, Munich, Salzburg, Brno) and generates consistent data for other locations using seeded randomization.

## Docker

```bash
docker build -t mcp-demographics .
docker run -p 8014:8014 -e API_KEY=your-key mcp-demographics
```
