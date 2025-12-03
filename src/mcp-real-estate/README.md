# mcp-real-estate

MCP server providing commercial property listings, rental rates, foot traffic data, and location analysis for coffee shop expansion planning.

## Tools

| Tool | Description |
|------|-------------|
| `mcp_realestate_search_properties` | Search available commercial spaces by city, district, size, rent |
| `mcp_realestate_get_rental_rates` | Get rental rate data (avg/min/max per sqm, trends) |
| `mcp_realestate_get_foot_traffic` | Get pedestrian traffic data (daily avg, peak hours) |
| `mcp_realestate_get_nearby_amenities` | Get nearby businesses, transit, competitors |
| `mcp_realestate_get_location_score` | Get composite location scores (walkability, transit, competition) |
| `mcp_realestate_get_vacancy_rates` | Get commercial vacancy rates and leasing times |
| `mcp_realestate_compare_locations` | Compare multiple locations side-by-side |

## Coverage

Mock data available for:
- **Brno**: Veveří, Královo Pole, Brno-střed, Židenice
- **Vienna**: Neubau, Mariahilf, Leopoldstadt, Josefstadt
- **Prague**: Karlín (reference location for Cofilot)

## Running Locally

```bash
cd src/mcp-real-estate
uv sync
uv run python main.py
```

Server runs on `http://localhost:8004`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_REALESTATE_API_KEY` | `dev-api-key` | API key for authentication |
| `MCP_REALESTATE_PORT` | `8004` | Server port |
| `MCP_REALESTATE_LOG_LEVEL` | `INFO` | Logging level |
