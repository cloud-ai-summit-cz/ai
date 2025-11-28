# Agent Location Scout

LangGraph-based agent hosted in Azure AI Foundry as a Hosted Agent for location analysis and market research.

## Overview

This agent analyzes business locations, evaluates market potential, assesses competition, and provides strategic recommendations for retail, commercial, or service-based business placement.

## Architecture

- **Framework**: LangGraph with `StateGraph` and `MessagesState`
- **Hosting**: Azure AI Foundry Hosted Agent (containerized)
- **Integration**: Uses `azure-ai-agentserver-langgraph` adapter package
- **API**: Invoked via Foundry Responses API (same as MAF agents)

## Prerequisites

- Python 3.12+
- Azure AI Foundry project with deployed model (e.g., GPT-4o)
- Docker (for containerized deployment)
- Azure CLI authenticated (`az login`)

## Local Development

### Setup

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
cd src/agent-location-scout
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your values
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_AI_FOUNDRY_ENDPOINT` | Foundry project endpoint | `https://your-project.region.api.azureml.ms` |
| `MODEL_DEPLOYMENT_NAME` | Deployed model name | `gpt-4o` |
| `CONTAINER_IMAGE_URI` | Container image URI | `ghcr.io/owner/agent-location-scout:latest` |

### Run Locally

```bash
# Run the agent server locally (for testing)
uv run python -m main
```

## Container Build

### Build Locally

```bash
docker build -t agent-location-scout:local .
```

### Run Container

```bash
docker run -p 8088:8088 \
  -e AZURE_AI_FOUNDRY_ENDPOINT=https://your-project.region.api.azureml.ms \
  -e MODEL_DEPLOYMENT_NAME=gpt-4o \
  agent-location-scout:local
```

## Deployment to Azure AI Foundry

### Provision Hosted Agent

```bash
# Create a new hosted agent version
uv run python provision.py create

# List existing versions
uv run python provision.py list

# Destroy a specific version
uv run python provision.py destroy --version 1
```

### CI/CD

The GitHub Actions workflow (`.github/workflows/agent-location-scout.yml`) automatically:
1. Runs linting and tests on PRs
2. Builds and pushes container to GHCR on main branch
3. Tags images with `latest`, `sha-<commit>`, and branch name

## Invoking the Agent

Once deployed, invoke via the Foundry Responses API:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str="your-connection-string"
)

response = client.agents.create_response(
    agent_name="location-scout",
    input="Analyze potential for a coffee shop in downtown Seattle near Pike Place Market"
)

print(response.output_text)
```

## Project Structure

```
src/agent-location-scout/
├── __init__.py           # Package marker
├── agent.py              # LangGraph agent definition
├── config.py             # Configuration (pydantic-settings)
├── main.py               # Entry point with from_langgraph
├── provision.py          # SDK-based deployment script
├── pyproject.toml        # Dependencies (uv)
├── Dockerfile            # Container definition
├── .env.example          # Environment template
├── prompts/
│   └── system_prompt.jinja2  # Agent system prompt
└── README.md             # This file
```

## Testing

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format --check .
```

## Related Documentation

- [Architecture Spec](../../specs/services/agent-location-scout/ARCHITECTURE.md)
- [Platform Architecture](../../specs/platform/ARCHITECTURE.md)
- [Azure AI Foundry Hosted Agents](https://learn.microsoft.com/azure/ai-studio/how-to/develop/hosted-agents)
