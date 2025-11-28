# Service Architecture: agent-finance-analyst

MAF-based agent for financial projections and analysis, deployed in Azure Container Apps and exposed via A2A protocol to demonstrate cross-platform agent communication.

## Context

- **Purpose**: Create financial projections, startup costs, operating costs, and break-even analysis. Demonstrates A2A protocol for external agent integration.
- **Upstream Dependencies**: research-orchestrator (via A2A Protocol)
- **Downstream Dependencies**: 
  - `mcp-scratchpad` (MCP Server) - shared workspace
  - `mcp-business-registry` (MCP Server) - company financials
  - `mcp-government-data` (MCP Server) - tax rates, regulations
  - `mcp-real-estate` (MCP Server) - rental rates
  - `mcp-calculator` (MCP Server) - financial calculations
  - Azure OpenAI (LLM)

## Component Diagram

```mermaid
flowchart TB
    subgraph Container["agent-finance-analyst (Container Apps)"]
        A2A[A2A Protocol Server]
        MAF[MAF Agent]
        Tools[MCP Tool Bindings]
        
        A2A --> MAF
        MAF --> Tools
    end
    
    subgraph Orchestrator["research-orchestrator"]
        ORCH[MAF Orchestrator]
    end
    
    subgraph MCP["MCP Servers"]
        SP[mcp-scratchpad]
        BR[mcp-business-registry]
        GOV[mcp-government-data]
        RE[mcp-real-estate]
        CALC[mcp-calculator]
    end
    
    subgraph Azure["Azure Services"]
        AOAI[Azure OpenAI]
        MI[Managed Identity]
    end
    
    ORCH -->|A2A Protocol| A2A
    MI -->|Auth| A2A
    Tools -->|MCP| SP
    Tools -->|MCP| BR
    Tools -->|MCP| GOV
    Tools -->|MCP| RE
    Tools -->|MCP| CALC
    MAF -->|LLM Calls| AOAI
```

## Data Flow

### A2A Invocation Flow

```mermaid
sequenceDiagram
    participant Orch as research-orchestrator
    participant A2A as A2A Server
    participant MAF as MAF Agent
    participant MCP as MCP Servers
    participant AOAI as Azure OpenAI
    
    Orch->>A2A: POST /a2a/tasks (A2A protocol)
    Note over A2A: Validate managed identity token
    A2A->>MAF: Route to agent
    
    MAF->>MCP: read_section(market_findings)
    MCP-->>MAF: Market data
    
    MAF->>MCP: read_section(location_options)
    MCP-->>MAF: Location data
    
    MAF->>MCP: calculate_startup_costs(...)
    MCP-->>MAF: Startup costs
    
    MAF->>MCP: calculate_operating_costs(...)
    MCP-->>MAF: Operating costs
    
    MAF->>MCP: create_revenue_projection(...)
    MCP-->>MAF: Revenue projection
    
    MAF->>AOAI: Generate analysis
    AOAI-->>MAF: Analysis text
    
    MAF->>MCP: write_section(financial_projections)
    
    MAF-->>A2A: Task result
    A2A-->>Orch: A2A response (streaming)
```

## Cross-Cutting Concerns

### Resilience Tactics
- **Retry**: MAF built-in retry on MCP failures
- **Timeout**: 60s per MCP call, 2min total execution
- **Circuit breaker**: On repeated MCP failures

### Performance Targets
| Metric | Target |
|--------|--------|
| A2A request latency | < 500ms (excluding agent execution) |
| Agent execution time | < 60s |
| MCP tool call latency | < 5s |

### A2A Protocol Compliance
- Implements [A2A Protocol](https://a2a-protocol.org/latest/)
- Supports task creation, status polling, and streaming responses
- Authentication via managed identity tokens

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Agent Framework | Microsoft Agent Framework | latest |
| A2A Server | Custom FastAPI implementation | 1.0 |
| HTTP Client | httpx | latest |
| Authentication | azure-identity | latest |
| Container | Python 3.11 slim | 3.11 |

## ADR References

- ADR-003: A2A for cross-platform agent communication (pending)
- ADR-006: Managed Identity for A2A authentication (pending)
