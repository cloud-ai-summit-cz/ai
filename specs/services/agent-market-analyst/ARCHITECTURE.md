# Service Architecture: agent-market-analyst

Foundry Native prompt-based agent for market research and analysis.

## Context

- **Purpose**: Research market size, growth trends, customer segments, and coffee culture for expansion analysis
- **Upstream Dependencies**: research-orchestrator (via Foundry SDK)
- **Downstream Dependencies**: 
  - `mcp-scratchpad` (MCP Server) - shared workspace
  - `mcp-web-search` (MCP Server) - web search, news, social media
  - `mcp-demographics` (MCP Server) - population, income, consumer data
  - Azure OpenAI (LLM - Foundry managed)

## Component Diagram

```mermaid
flowchart TB
    subgraph Foundry["AI Foundry (Managed)"]
        Agent[market-analyst Agent]
        Thread[Agent Thread]
    end
    
    subgraph Orchestrator["research-orchestrator"]
        ORCH[MAF Orchestrator]
    end
    
    subgraph MCP["MCP Servers"]
        SP[mcp-scratchpad]
        WS[mcp-web-search]
        DM[mcp-demographics]
    end
    
    ORCH -->|Foundry SDK| Agent
    Agent <--> Thread
    Agent -->|MCP| SP
    Agent -->|MCP| WS
    Agent -->|MCP| DM
```

## Agent Definition

### System Prompt
```
You are a market research analyst specializing in the coffee and café industry.
Your role is to research and analyze market data for potential expansion locations.

Tasks:
1. Research market size and growth trends for the target city
2. Identify customer segments and their preferences
3. Analyze local coffee culture and consumption patterns
4. Document findings in the scratchpad

Always:
- Start by checking if any previous research exists in the scratchpad
- Use the market data tools to gather quantitative data
- Write detailed findings to the scratchpad when complete
- Update the checklist to mark your task as complete
```

### MCP Tools
| Tool | Server | Purpose |
|------|--------|--------|
| `read_section` | mcp-scratchpad | Read existing research |
| `write_section` | mcp-scratchpad | Store findings |
| `update_checklist` | mcp-scratchpad | Update progress |
| `search_web` | mcp-web-search | Search web for market info |
| `search_news` | mcp-web-search | Search recent news articles |
| `search_social_media` | mcp-web-search | Search social media trends |
| `get_population_stats` | mcp-demographics | Get population data |
| `get_income_distribution` | mcp-demographics | Get income/purchasing power |
| `get_consumer_spending` | mcp-demographics | Get spending patterns |
| `get_lifestyle_segments` | mcp-demographics | Get consumer segments |

## Cross-Cutting Concerns

### Performance Targets
| Metric | Target |
|--------|--------|
| Agent execution time | < 30s |
| MCP tool call latency | < 5s |

### Resilience
- Foundry-managed retry and error handling
- MCP tool timeout: 30s

## Provisioning

Agent is provisioned via Python script using `azure-ai-projects` SDK:

```python
agent = client.agents.create(
    name="market-analyst",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions=SYSTEM_PROMPT,
        # NOTE: No tools configured here - see MCP Session Isolation below
    ),
    description="Market research analyst for expansion analysis"
)
```

## MCP Session Isolation

> **Important Architecture Decision**: MCP tools are NOT configured at agent provisioning time.

### Why Not Provision-Time MCP?

1. **Azure AI Foundry Limitation**: The `MCPTool` class does not allow sensitive headers (like `Authorization`) in the agent definition. You must use `project_connection_id` or pass headers via `tool_resources` at runtime.

2. **Session Isolation Requirement**: Each research session needs a unique `X-Session-ID` header to isolate scratchpad data. This session ID is only known at runtime when the orchestrator creates a research session.

3. **Audit Trail**: The `X-Caller-Agent` header identifies which agent made each MCP call, enabling proper audit logging.

### How It Works

```mermaid
sequenceDiagram
    participant UI as Web UI
    participant Orch as Orchestrator
    participant MCP as mcp-scratchpad
    participant Agent as market-analyst
    
    UI->>Orch: Start research session
    Orch->>Orch: Generate session_id
    
    Note over Orch: Create session-scoped MCP tool
    Orch->>Orch: MCPStreamableHTTPTool(<br/>headers={<br/>  "Authorization": "Bearer ...",<br/>  "X-Session-ID": session_id,<br/>  "X-Caller-Agent": "market-analyst"<br/>})
    
    Orch->>Agent: Invoke with tools=[session_mcp]
    Agent->>MCP: read_section() [with session headers]
    MCP-->>Agent: Session-scoped data only
```

### Security Benefits

| Concern | Solution |
|---------|----------|
| Cross-session data access | `X-Session-ID` header isolates data per session |
| Credential exposure | Bearer token injected by orchestrator, not stored in agent definition |
| Agent impersonation | `X-Caller-Agent` header set by orchestrator, not agent |
| Audit logging | All MCP calls tagged with session and caller info |
