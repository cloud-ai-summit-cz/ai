# Finance Analyst A2A Agent

Finance Analyst agent exposed via Agent-to-Agent (A2A) protocol using Microsoft Agent Framework.

## Overview

This agent specializes in financial analysis for coffee shop expansion projects. It provides:

- **Startup Cost Analysis**: Equipment, renovation, licensing, initial inventory
- **Operating Cost Analysis**: Rent, labor, utilities, supplies, marketing
- **Revenue Projections**: Based on foot traffic, market size, pricing strategy
- **Break-even Analysis**: Time to profitability calculations
- **ROI & NPV Calculations**: Investment return metrics
- **Cash Flow Projections**: Monthly/annual cash flow forecasting
- **Sensitivity Analysis**: Risk assessment on key variables

## Tools

The agent uses the following tools:

1. **MCP Calculator** (primary) - Financial calculations (startup costs, operating costs, revenue projections, break-even, ROI, NPV, cash flow, sensitivity analysis)
2. **MCP Real Estate** - Property listings and rental rates
3. **MCP Government Data** - Tax rates, regulations, licensing requirements
4. **MCP Business Registry** - Competitor financial benchmarks
5. **MCP Scratchpad** - Persistent storage for analysis notes and findings
6. **Bing Web Search** - Current market rates and financial benchmarks

## Prerequisites

- Python 3.11+
- Azure OpenAI deployment with GPT-4.1
- Azure credentials configured (DefaultAzureCredential)
- Running MCP servers (calculator, real-estate, government-data, business-registry, scratchpad)

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. Configure your Azure OpenAI endpoint and MCP server URLs in `.env`

## Running

```bash
uv run python main.py
```

The server will start on `http://localhost:8022` by default.

## API Endpoints

- `GET /health` - Health check
- `GET /.well-known/agent.json` - Agent card (A2A discovery)
- `POST /` - A2A task execution

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name | `gpt-4.1` |
| `MCP_CALCULATOR_URL` | Calculator MCP server URL | `http://localhost:8006` |
| `MCP_REAL_ESTATE_URL` | Real Estate MCP server URL | `http://localhost:8005` |
| `MCP_GOVERNMENT_DATA_URL` | Government Data MCP server URL | `http://localhost:8004` |
| `MCP_BUSINESS_REGISTRY_URL` | Business Registry MCP server URL | `http://localhost:8003` |
| `MCP_SCRATCHPAD_URL` | Scratchpad MCP server URL | `http://localhost:8001` |
| `A2A_SERVER_PORT` | Server port | `8022` |
| `A2A_SERVER_API_KEY` | API key for authentication | Optional |

## A2A Skills

The agent exposes the following skills:

1. **financial-analysis** - Comprehensive financial analysis
2. **cost-estimation** - Startup and operating cost estimation
3. **revenue-projection** - Revenue forecasting
4. **investment-metrics** - ROI, NPV, IRR, payback calculations
5. **sensitivity-analysis** - Risk factor analysis

## Session Isolation

The agent supports session isolation via the `X-Session-ID` header. This header is passed through to MCP servers to ensure data isolation between different research sessions.
