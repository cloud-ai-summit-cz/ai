# Cofilot AI Platform - Local Development Runner

This folder contains the local development runner for starting all agents and MCP servers.

## Quick Start

```powershell
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Start all services
uv run python run_all.py

# Or list available services first
uv run python run_all.py --list
```

## Configuration

Edit `config.yaml` to control which services to start:

```yaml
# Disable specific MCP servers
mcp_servers:
  scratchpad:
    enabled: true
  web-search:
    enabled: false  # Disable this one

# Disable specific agents
agents:
  market-analyst:
    enabled: false  # Skip provisioning
```

## Log Output

All services stream logs to a single terminal with color-coded tags:

```
[age-market-analyst] Creating Market Analyst Agent
[age-market-analyst] [OK] Created Market Analyst (ID: market-analyst)
[mcp-scratchpad    ] INFO:     Started server process [12345]
[mcp-web-search    ] INFO:     Uvicorn running on http://0.0.0.0:8011
[age-location-scout] Starting Location Scout agent...
```

## Services

### Agents (6 total)

| Agent | Type | Mode |
|-------|------|------|
| `research-orchestrator` | MAF | Long-running service |
| `market-analyst` | Foundry Native | Provision only (creates agent in Azure) |
| `competitor-analyst` | Foundry Native | Provision only (creates agent in Azure) |
| `location-scout` | LangGraph | Long-running service |
| `finance-analyst` | LangGraph | Long-running service |
| `synthesizer` | Foundry Native | Provision only (creates agent in Azure) |

**Note**: Foundry Native agents run their provisioning scripts (idempotent create) then exit. They don't run as local services - the actual agent runs in Azure AI Foundry.

### MCP Servers (7 total)

| Server | Port |
|--------|------|
| `mcp-scratchpad` | 8010 |
| `mcp-web-search` | 8011 |
| `mcp-business-registry` | 8012 |
| `mcp-government-data` | 8013 |
| `mcp-demographics` | 8014 |
| `mcp-real-estate` | 8015 |
| `mcp-calculator` | 8016 |

## Command Line Options

```
usage: run_all.py [-h] [--config CONFIG] [--env ENV] [--list]

options:
  -h, --help            show this help message and exit
  --config, -c CONFIG   Path to config file (default: config.yaml)
  --env, -e ENV         Path to .env file (default: .env)
  --list, -l            List available services and exit
```

## Stopping Services

Press `Ctrl+C` to gracefully stop all services.

## Testing the Research Orchestrator

A test script is provided to validate the Research Orchestrator API:

```powershell
# First, start the orchestrator
# In one terminal:
cd ../../src/agent-research-orchestrator
uv sync
uv run python -m research_orchestrator.main

# Then run the test script in another terminal:
cd deploy/local
uv sync
uv run python test_orchestrator.py

# Options:
uv run python test_orchestrator.py --help
uv run python test_orchestrator.py --health-only  # Just check connectivity
uv run python test_orchestrator.py --url http://localhost:8000  # Custom URL
uv run python test_orchestrator.py --query "Your custom research query"
```

The test script will:
1. Check API health and Foundry connectivity
2. Verify required agents are provisioned
3. Create a research session
4. Start the workflow and stream SSE events
5. Display the final synthesis results
