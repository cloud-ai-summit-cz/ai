# Competitor Analyst A2A Agent (MAF)

Standalone A2A (Agent-to-Agent) implementation of the Competitor Analyst using Microsoft Agent Framework.

## Overview

This agent specializes in competitive landscape analysis for Cofilot's specialty coffee business expansion. It uses:

- **MCP Business Registry**: For company data, profiles, financials, and industry players
- **MCP Scratchpad**: For session-scoped collaboration with other research agents
- **Grounded Web Search (Bing)**: Built-in web search via Azure OpenAI's Grounding with Bing

## Features

- A2A protocol compliant server
- Session-scoped MCP tool access via `X-Session-ID` header
- API key authentication support
- Azure managed identity for Azure OpenAI and MCP authentication

## Local Development

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the server:
   ```bash
   uv run main.py
   ```

4. Test the agent card endpoint:
   ```bash
   curl http://localhost:8021/.well-known/agent-card.json
   ```

## Docker Build

From the `src/agent-competitor-analyst` directory:

```bash
docker build -f standalone/a2a/maf/Dockerfile -t competitor-analyst-a2a .
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Yes |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name | Yes |
| `MCP_BUSINESS_REGISTRY_URL` | MCP Business Registry endpoint | Yes |
| `MCP_BUSINESS_REGISTRY_API_KEY` | API key for Business Registry | Yes |
| `MCP_SCRATCHPAD_URL` | MCP Scratchpad endpoint | Yes |
| `MCP_SCRATCHPAD_API_KEY` | API key for Scratchpad | Yes |
| `A2A_SERVER_PORT` | Server port (default: 8021) | No |
| `A2A_PUBLIC_HOST` | Public hostname for agent card | No |
| `A2A_API_KEY` | API key for authentication | Recommended |

## A2A Skills

1. **Competitor Identification**: Map all relevant players in the market
2. **Competitor Profiling**: Detailed profiles of top competitors
3. **Positioning Analysis**: Market positioning and white space identification
4. **Competitive Threats**: Barrier to entry and threat assessment
