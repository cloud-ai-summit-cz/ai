# Architecture Decision Record (ADR)

- **ADR ID**: ADR-006
- **Title**: Move MCP Tool Execution from Foundry Agent Service to MAF Orchestrator
- **Status**: Accepted
- **Date**: 2025-12-03
- **Authors**: Platform Team
- **Related Docs**: `ADR-005-realtime-agent-observability.md`, `specs/services/agent-research-orchestrator/ARCHITECTURE.md`

---

## 1. Context

### Business Problem

The Research UI requires real-time visibility into MCP tool calls made by subagents (market-analyst, competitor-analyst, synthesizer). Currently, when these agents call MCP tools like `mcp-demographics`, `mcp-business-registry`, or `mcp-government-data`, the execution happens **server-side in Azure AI Foundry Agent Service**, which means:

1. **No real-time streaming**: MAF's `stream_callback` only receives text tokens, not `FunctionCallContent` for server-side tool executions
2. **Delayed visibility**: We must poll Application Insights for traces (2-8 second latency per ADR-005)
3. **Complex architecture**: The trace polling mechanism adds significant complexity

### Technical Driver

Current architecture:

```
UI → Orchestrator (MAF) → Subagent (Foundry) → MCP Tools (server-side execution)
                                                      ↑ No visibility via stream_callback
```

The `mcp-scratchpad` already works differently - it's configured in the orchestrator with `MCPStreamableHTTPTool` and injected into subagents at runtime. This provides:
- Full visibility via MAF middleware
- Real-time SSE events
- Session isolation via `X-Session-ID` headers

### Constraints

| Constraint | Impact |
|------------|--------|
| Demo deadline: December 8, 2025 | Must be quick to implement |
| Existing scratchpad pattern | Can reuse proven architecture |
| Foundry MCPTool limitations | Cannot pass sensitive headers at provisioning time |
| Session isolation required | Only for scratchpad; other MCP servers are read-only reference data |

### Existing Environment

- `mcp-scratchpad` already uses `MCPStreamableHTTPTool` in orchestrator
- Middleware intercepts all tool calls with full input/output capture
- SSE streaming infrastructure is mature and working
- MCP servers (demographics, business-registry, government-data) are deployed and functional

---

## 2. Decision Statement

**Move MCP tool execution for `mcp-government-data`, `mcp-demographics`, and `mcp-business-registry` from Foundry Agent Service (server-side) to MAF Orchestrator (client-side) using `MCPStreamableHTTPTool`.**

The orchestrator will:
1. Create `MCPStreamableHTTPTool` instances for each MCP server
2. Inject appropriate tools into each subagent based on their role
3. Capture tool calls via existing MAF middleware
4. Stream events directly via SSE (no polling needed)

Subagents in Foundry become **prompt-only agents** with no MCP tools configured at provisioning time.

---

## 3. Specification by Example Snapshot

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Real-time tool visibility | market-analyst invoked | Agent calls `mcp-demographics.get_population_stats()` | SSE emits `tool_call_started` within 500ms |
| Tool execution in MAF | competitor-analyst invoked | Agent calls `mcp-business-registry.search_companies()` | Middleware captures full input/output |
| No trace polling needed | Research session running | MCP tools called | Direct SSE events; no App Insights polling required |
| Subagent tool injection | Orchestrator creates market-analyst | Agent created with tools | Agent has [scratchpad, demographics] tools |

---

## 4. Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Orchestrator-managed MCP tools (SELECTED)** | Move MCP tool execution to MAF orchestrator using `MCPStreamableHTTPTool` | Real-time SSE; simpler architecture; proven pattern (scratchpad); full observability | Requires code changes in orchestrator and agent provisioning |
| **B. Keep server-side + trace polling (current)** | Continue using Foundry Agent Service for MCP execution | No changes needed | 2-8s latency; complex polling; poor demo experience |
| **C. Custom MCP proxy in orchestrator** | Build a proxy that intercepts MCP calls | Could add caching/filtering | Extra complexity; reinventing MCPStreamableHTTPTool |
| **D. Foundry connections with trace export** | Use project_connection_id and accept trace polling latency | Uses Foundry native features | Still has latency; connection management complexity |

---

## 5. Decision Drivers

1. **Real-time demo visibility** - Tool calls must appear instantly in UI
2. **Simplicity** - Reuse existing scratchpad pattern
3. **Lower latency** - From 2-8s (trace polling) to <500ms (direct SSE)
4. **Maintainability** - Remove trace polling complexity
5. **Implementation speed** - Pattern already proven; estimated 2 days

---

## 6. Consequences

### Positive Outcomes
- **Real-time SSE streaming** for all MCP tool calls
- **Simplified architecture** - can remove/disable trace polling for MCP visibility
- **Full input/output capture** in middleware for debugging
- **Consistent pattern** across all MCP tools (scratchpad and others)
- **Lower latency** - 500ms vs 2-8 seconds

### Trade-offs / Risks
- **Subagent autonomy unchanged** - Agents still decide what tools to call via function calling
- **Configuration in orchestrator** - MCP URLs/keys now in orchestrator config (not Foundry connections)
- **More tools in orchestrator** - Orchestrator manages more MCP connections

### Operational Impacts
- **Foundry connections** - Can remove `mcp-*` connection resources from Terraform (optional)
- **Agent provisioning** - Subagents become prompt-only (no MCPTool in definition)
- **Monitoring** - Tool call telemetry now in orchestrator logs

---

## 7. Implementation Plan

### Phase 1: Orchestrator Config Updates
- [x] Add MCP settings to orchestrator config for:
  - `mcp-demographics` (URL, API key)
  - `mcp-business-registry` (URL, API key)
  - `mcp-government-data` (URL, API key)

### Phase 2: Orchestrator Tool Injection
- [x] Create `_create_mcp_tools_for_agent()` helper method
- [x] Map agent roles to required MCP tools:
  - `market-analyst`: scratchpad, demographics
  - `competitor-analyst`: scratchpad, business-registry
  - `synthesizer`: scratchpad only (or calculator if needed)
- [x] Inject tools when creating subagent ChatAgent instances

### Phase 3: Agent Provisioning Updates
- [x] Update `market-analyst/provision.py` - remove MCPTool definitions
- [x] Update `competitor-analyst/provision.py` - remove MCPTool definitions
- [x] (Optional) Update `synthesizer/provision.py` if it has MCP tools

### Phase 4: Cleanup (Optional)
- [ ] Disable trace polling for MCP tool visibility (keep for other traces)
- [ ] Remove Foundry connection resources from Terraform
- [ ] Update documentation

### Telemetry/Metrics to Monitor
| Metric | Target | Alert |
|--------|--------|-------|
| `mcp_tool_call_latency_ms` | < 500ms | > 1000ms |
| `mcp_tool_call_success_rate` | > 99% | < 95% |
| `sse_event_delivery_latency_ms` | < 500ms | > 1000ms |

### Owners
- Implementation: Platform Team
- Testing: Platform Team

---

## 8. Verification

### Tests That Prove the Decision Works
1. **SSE streaming test**: Invoke subagent → verify MCP tool call appears in SSE within 500ms
2. **Middleware capture test**: Call MCP tool → verify input/output logged in middleware
3. **Agent isolation test**: Each agent only has its designated MCP tools available
4. **End-to-end test**: Full research workflow completes with visible tool calls

### Rollback Plan
If issues arise:
1. Re-add MCPTool definitions to agent provisioning
2. Re-enable trace polling for MCP visibility
3. Orchestrator MCP tools become redundant (no harm)

---

## 9. MCP Tool to Agent Mapping

| Agent | MCP Tools (Orchestrator-injected) | Purpose |
|-------|-----------------------------------|---------|
| `market-analyst` | `mcp-scratchpad`, `mcp-demographics` | Population, income, consumer behavior data |
| `competitor-analyst` | `mcp-scratchpad`, `mcp-business-registry` | Company profiles, financials, industry players |
| `synthesizer` | `mcp-scratchpad` | Report compilation |
| `location-scout` | `mcp-scratchpad`, `mcp-government-data`, `mcp-demographics`, `mcp-real-estate` | (Foundry Hosted - separate consideration) |
| `finance-analyst` | `mcp-scratchpad`, `mcp-calculator`, `mcp-business-registry` | (A2A - separate consideration) |

> **Note**: This ADR covers `market-analyst`, `competitor-analyst`, and `synthesizer` (Foundry Native agents). Location-scout (Foundry Hosted) and finance-analyst (A2A) may require separate consideration.

---

## 10. Change Log

| Date | Author | Update |
|------|--------|--------|
| 2025-12-03 | Platform Team | Initial ADR created |
