# Market Analyst A2A Agent (Microsoft Agent Framework)

A standalone Market Analyst agent implemented using the **Microsoft Agent Framework** with **A2A (Agent-to-Agent) protocol** support for inter-agent communication and **MCP (Model Context Protocol)** integration for real-time demographic data.

## Overview

This implementation exposes the Market Analyst agent as an **A2A-compliant service** that can be discovered and invoked by other A2A-capable agents. The agent uses:

- **Microsoft Agent Framework** with `AzureOpenAIResponsesClient` for AI capabilities
- **Azure OpenAI** with `gpt-5` model for inference
- **A2A Protocol** for standardized agent-to-agent communication
- **MCP Demographics Tool** for real-time demographic and consumer behavior data

### A2A Protocol Integration

The A2A (Agent-to-Agent) protocol is an open standard that enables AI agents from different vendors and frameworks to communicate and collaborate. Key concepts:

- **AgentCard**: A JSON metadata document describing the agent's capabilities, skills, and how to interact with it
- **Tasks**: The fundamental unit of work, with states (submitted, working, completed, failed, canceled)
- **Messages**: Communication turns between client and agent containing Parts (text, file, data)
- **Skills**: Specific capabilities the agent can perform

Since Microsoft Agent Framework's built-in A2A hosting for Python is still in development, this implementation uses the [a2a-sdk](https://pypi.org/project/a2a-sdk/) Python package to provide A2A protocol compliance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    A2A Client (Other Agents)                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ A2A Protocol (HTTP+JSON)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      A2A Server Layer                            │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │  AgentCard   │  │  Task Manager   │  │  Message Handler   │  │
│  │  Discovery   │  │  (State Mgmt)   │  │  (Send/Stream)     │  │
│  └──────────────┘  └─────────────────┘  └────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              MarketAnalystExecutor (AgentExecutor)               │
│  - Receives A2A messages                                         │
│  - Invokes MAF agent                                             │
│  - Returns A2A-formatted responses                               │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MarketAnalystAgent                             │
│  - Microsoft Agent Framework (AzureOpenAIResponsesClient)        │
│  - Azure OpenAI gpt-5 model                                      │
│  - Market analysis system prompt                                 │
│  - MCP Demographics Tool (MCPStreamableHTTPTool)                 │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ MCP Protocol (HTTP)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Demographics Server                       │
│  - Population statistics                                         │
│  - Income distribution                                           │
│  - Age distribution                                              │
│  - Consumer spending patterns                                    │
│  - Lifestyle segments                                            │
│  - Commuter patterns                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Azure OpenAI deployment with `gpt-5` model
- Azure CLI authenticated (`az login`)

## Installation

```bash
# Navigate to the agent directory
cd src/agent-market-analyst/standalone/a2a/maf

# Create and configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI settings

# Install dependencies with uv
uv sync
```

## Configuration

Set the following environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://myresource.openai.azure.com/` |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name | `gpt-5` |
| `AZURE_OPENAI_API_VERSION` | API version | `preview` |
| `MCP_DEMOGRAPHICS_URL` | MCP Demographics server URL | `https://your-server/mcp` |
| `MCP_DEMOGRAPHICS_API_KEY` | API key for MCP Demographics | `your-api-key` |
| `A2A_SERVER_HOST` | Server bind address | `0.0.0.0` |
| `A2A_SERVER_PORT` | Server port | `8020` |

## Running the Agent

```bash
# Run with uv
uv run python main.py

# Or run directly after installing
python main.py
```

The agent will start and display:

```
Starting Market Analyst A2A Agent
  Name: Market Analyst Agent
  Host: 0.0.0.0
  Port: 8020
  Model: gpt-5
  Agent Card: http://0.0.0.0:8020/.well-known/agent-card.json
```

## A2A Endpoints

Once running, the agent exposes these A2A-compliant endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/agent-card.json` | GET | AgentCard (agent discovery) |
| `/` | POST | Send a message to the agent (JSON-RPC) |

## Example Usage

### Discover the Agent

```bash
curl http://localhost:8020/.well-known/agent-card.json
```

Response (AgentCard):
```json
{
  "name": "Market Analyst Agent",
  "description": "Market analysis specialist for Cofilot's coffee business expansion...",
  "version": "1.0.0",
  "protocolVersion": "1.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "market-sizing",
      "name": "Market Size Analysis",
      "description": "Analyze TAM/SAM/SOM for specialty coffee..."
    }
  ]
}
```

### Send a Message

```bash
curl -X POST http://localhost:8020/v1/message:send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "messageId": "msg-001",
      "role": "user",
      "parts": [
        {"text": "What is the market size for specialty coffee in Brno, Czech Republic?"}
      ]
    }
  }'
```

Response:
```json
{
  "task": {
    "id": "task-uuid",
    "contextId": "context-uuid",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "artifactId": "artifact-uuid",
        "name": "Market Analysis Response",
        "parts": [
          {"text": "The specialty coffee market in Brno..."}
        ]
      }
    ]
  }
}
```

## Connecting from Another A2A Agent

Other A2A-compliant agents can discover and use this agent:

```python
# Using agent-framework-a2a
from agent_framework.a2a import A2AAgent

agent = A2AAgent(
    name="Market Analyst",
    description="Market analysis agent",
    url="http://localhost:8020"
)

result = await agent.run("What is the TAM for specialty coffee in Vienna?")
print(result.text)
```

## Agent Skills

The Market Analyst agent provides three main skills:

1. **Market Size Analysis** (`market-sizing`)
   - TAM/SAM/SOM calculations
   - Market valuation
   - Geographic market analysis

2. **Consumer Behavior Analysis** (`consumer-analysis`)
   - Customer segmentation
   - Demographics analysis
   - Spending patterns

3. **Market Trends & Dynamics** (`market-trends`)
   - Growth trends
   - Industry dynamics
   - Market opportunities

## Development

### Run Tests

```bash
uv run pytest tests/ -v
```

### Type Checking

```bash
uv run mypy .
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Docker / Container Deployment

### Building the Container

The agent includes a `Dockerfile` for containerized deployment. The build context must be set to the parent `agent-market-analyst` directory to include the `prompts/` folder.

```bash
# From the repository root
cd src/agent-market-analyst
docker build -f standalone/a2a/maf/Dockerfile -t agent-market-analyst-a2a:latest .
```

### Using the Build Script

The agent is also included in the ACR build configuration:

```bash
# Build using ACR Tasks (remote build, no local Docker needed)
cd deploy/azure
python build.py --container agent-market-analyst-a2a
```

### Running the Container

```bash
docker run -d \
  --name market-analyst-a2a \
  -p 8020:8020 \
  -e AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/ \
  -e MODEL_DEPLOYMENT_NAME=gpt-5 \
  -e A2A_PUBLIC_HOST=your-hostname \
  -e A2A_API_KEY=your-secret-key \
  agent-market-analyst-a2a:latest
```

### Required Environment Variables for Container

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name (default: `gpt-5`) |
| `MCP_DEMOGRAPHICS_URL` | MCP Demographics server URL |
| `MCP_DEMOGRAPHICS_API_KEY` | API key for MCP Demographics |
| `A2A_PUBLIC_HOST` | Public hostname for AgentCard URL |
| `A2A_API_KEY` | API key for authentication |

Note: In containers, `PROMPTS_DIR_OVERRIDE` is automatically set to `/app/prompts`.

## MCP Demographics Integration

The agent uses the **MCP Demographics** service via `MCPStreamableHTTPTool` to retrieve real-time demographic data. Available tools:

| Tool | Description |
|------|-------------|
| `mcp_demographics_get_population_stats` | Population count, density, growth rate |
| `mcp_demographics_get_income_distribution` | Income levels, purchasing power, unemployment |
| `mcp_demographics_get_age_distribution` | Age group percentages, dependency ratio |
| `mcp_demographics_get_consumer_spending` | Spending by category |
| `mcp_demographics_get_lifestyle_segments` | Consumer segmentation analysis |
| `mcp_demographics_get_commuter_patterns` | Foot traffic and commute patterns |

## References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Azure OpenAI Responses Agent](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-types/azure-openai-responses-agent)
- [A2A Python SDK](https://pypi.org/project/a2a-sdk/)
