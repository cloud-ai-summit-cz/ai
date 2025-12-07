# Competitor Analyst Agent

Analyzes competitive landscape for Cofilot's expansion to Brno and Vienna.

## Agent Structure

```
agent-competitor-analyst/
├── prompts/
│   └── system_prompt.md          # Agent instructions (plain markdown)
│
├── standalone/                    # Self-hosted agent variants
│   ├── a2a/                       # A2A protocol servers
│   │   ├── maf/                   # Microsoft Agent Framework implementation
│   │   └── langgraph/             # LangGraph implementation
│   │
│   └── foundry/                   # Azure AI Foundry hosted agents
│       ├── maf/                   # MAF-based hosted agent
│       └── langgraph/             # LangGraph-based hosted agent
│
├── provision_foundry_agent_base.py   # Create prompt-only agent in Foundry
├── provision_foundry_agent_full.py   # Create agent with MCP tools in Foundry (future)
├── config.py                         # Shared configuration
└── pyproject.toml                    # Python dependencies
```

## Deployment Options

### Option 1: Foundry Prompt Agent (Current)

Agent lives in Azure AI Foundry as a prompt-only definition. The research orchestrator:
- References the agent by name
- Injects MCP tools at runtime (scratchpad, business-registry)
- Manages tool execution with SSE streaming

```bash
uv run python provision_foundry_agent_base.py create
```

### Option 2: Foundry Full Agent (Future)

Agent in Foundry with MCP tools configured directly. Uses Project Connections for auth.

```bash
uv run python provision_foundry_agent_full.py create
```

### Option 3: Standalone A2A Server (Future)

Self-hosted agent exposing A2A protocol. Can use MAF or LangGraph.

```bash
# MAF variant
cd standalone/a2a/maf
uv run python main.py

# LangGraph variant  
cd standalone/a2a/langgraph
uv run python main.py
```

### Option 4: Foundry Hosted Agent (Future)

Containerized agent deployed to Foundry as a hosted agent.

```bash
# Build container
./build.sh

# Deploy to Foundry
cd standalone/foundry/langgraph
uv run python provision.py deploy
uv run python provision.py start
```

## Container Naming Convention

When building containers, the naming follows:
`{agent-name}-{protocol}-{framework}`

Examples:
- `competitor-analyst-a2a-maf`
- `competitor-analyst-a2a-langgraph`
- `competitor-analyst-foundry-maf`
- `competitor-analyst-foundry-langgraph`

## MCP Tools

This agent uses the following MCP servers (injected by orchestrator):
- **mcp-scratchpad**: Shared workspace for notes and drafts
- **mcp-business-registry**: Company data, financials, industry players

## Development

```bash
# Install dependencies
uv sync

# Provision to Foundry
uv run python provision_foundry_agent_base.py create

# List agents
uv run python provision_foundry_agent_base.py list

# Destroy agent
uv run python provision_foundry_agent_base.py destroy
```

## Authentication

Uses `DefaultAzureCredential` - run `az login` first or configure managed identity.
