# Agent Research Orchestrator

MAF-based orchestrator agent for coordinating multi-agent research workflows using Microsoft Agent Framework.

## Overview

This service orchestrates research tasks across multiple specialist agents deployed in Azure AI Foundry:

- **market-analyst**: Analyzes market opportunities and trends
- **competitor-analyst**: Analyzes competitive landscape
- **synthesizer**: Combines insights into actionable recommendations

The orchestrator also integrates with **MCP Scratchpad** for inter-agent collaboration:
- Shared workspace for storing research findings
- Human-in-the-loop question queue
- Document collaboration across agents

The orchestrator exposes a REST API with SSE (Server-Sent Events) streaming for real-time progress updates.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Research Orchestrator                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │  FastAPI    │  │   MAF       │  │  SSE Publisher      │     │
│  │  REST API   │──│  Engine     │──│  (Event Streaming)  │     │
│  └─────────────┘  └─────────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼───────────────────┐
        │                  │                   │
        ▼                  ▼                   ▼
┌──────────────┐  ┌──────────────┐    ┌──────────────┐
│ Foundry      │  │ Foundry      │    │ MCP          │
│ Agents       │  │ Agents       │    │ Scratchpad   │
│              │  │              │    │ (Shared)     │
└──────────────┘  └──────────────┘    └──────────────┘
 market-analyst   competitor-analyst   write_section
 synthesizer                           read_section
                                       add_question
```

## Workflow

1. **Dynamic Orchestration**: The orchestrator autonomously decides which agents to call
2. **Parallel Execution**: Multiple agents can be invoked concurrently
3. **Scratchpad Collaboration**: Agents share findings via MCP Scratchpad
4. **Synthesis**: Final report synthesized from all gathered insights

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with Foundry connectivity status |
| POST | `/research/sessions` | Create a new research session |
| GET | `/research/sessions` | List all sessions |
| GET | `/research/sessions/{id}` | Get session details |
| POST | `/research/sessions/{id}/start` | Start session (returns SSE stream) |

## Usage

### Prerequisites

1. Provision the specialist agents to Azure AI Foundry:
   ```bash
   cd ../agent-market-analyst && uv run python -m market_analyst.provision create
   cd ../agent-competitor-analyst && uv run python -m competitor_analyst.provision create
   cd ../agent-synthesizer && uv run python -m synthesizer.provision create
   ```

2. Set environment variables:
   ```bash
   export FOUNDRY_ENDPOINT="https://your-project.services.ai.azure.com/api/projects/your-project"
   export MODEL_DEPLOYMENT_NAME="gpt-5"
   ```

### Running the Service

```bash
# Install dependencies
uv sync

# Run the API server
uv run python -m research_orchestrator.main
```

The API will be available at `http://localhost:8000`.

### Example: Running a Research Session

```bash
# Create a session
curl -X POST http://localhost:8000/research/sessions \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze the market opportunity for a new coffee shop in Prague 2"}'

# Start the session (SSE stream)
curl -N http://localhost:8000/research/sessions/{session_id}/start
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | (required) | Azure AI Foundry project endpoint |
| `MODEL_DEPLOYMENT_NAME` | `gpt-5` | Model deployment name |
| `MCP_SCRATCHPAD_URL` | (optional) | URL to MCP Scratchpad server (e.g., `https://ca-mcp-scratchpad.../mcp`) |
| `MCP_SCRATCHPAD_API_KEY` | (optional) | API key for MCP Scratchpad authentication |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `AGENT_TIMEOUT_SECONDS` | `60` | Individual agent timeout |
| `WORKFLOW_TIMEOUT_SECONDS` | `300` | Total workflow timeout |

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Type checking
uv run mypy research_orchestrator

# Linting
uv run ruff check research_orchestrator
```

## SSE Events

The `/research/sessions/{id}/start` endpoint streams the following events:

| Event | Description |
|-------|-------------|
| `session_started` | Workflow has begun |
| `agent_started` | An agent has started processing |
| `agent_completed` | An agent has finished successfully |
| `agent_failed` | An agent has encountered an error |
| `synthesis_started` | Synthesizer has started |
| `synthesis_completed` | Final synthesis is ready |
| `workflow_completed` | All processing complete |
| `workflow_failed` | Workflow encountered an error |
