# Architecture Decision Record (ADR)

- **ADR ID**: ADR-005
- **Title**: Real-time Agent Observability via OpenTelemetry and Application Insights
- **Status**: Accepted
- **Date**: 2025-12-01
- **Authors**: Platform Team
- **Related Docs**: `specs/platform/OBSERVABILITY.md`, `specs/services/agent-research-orchestrator/ARCHITECTURE.md`

---

## 1. Context

### Business Problem

The Research UI must show real-time visibility into:
1. **Orchestrator-level events**: "📤 Delegating to market-analyst", "📥 Response received from location-scout"
2. **Subagent tool calls**: When `market-analyst` calls `mcp-scratchpad.add_note()` or `location-scout` calls `mcp-real-estate.get_rental_rates()`

This visibility is critical for **demo audiences** to understand the multi-agent workflow as it executes.

### Technical Driver

Initial implementation attempted to use Microsoft Agent Framework's `stream_callback` to capture subagent tool calls:

```python
# ❌ This approach FAILS for Foundry Hosted Agents
def create_subagent_stream_callback(agent_name: str):
    async def callback(update: AgentRunResponseUpdate):
        if isinstance(update.content, FunctionCallContent):
            await emit_sse({"type": "tool_call", "tool": update.content.name})
    return callback
```

**Root Cause**: Azure AI Foundry Hosted Agents execute tools **server-side**. The `stream_callback` only receives text tokens, not `FunctionCallContent` or `FunctionResultContent` from hosted agent tool executions.

### Constraints

| Constraint | Impact |
|------------|--------|
| Azure AI Foundry architecture | Tools execute server-side; no stream-back of tool calls |
| Research sessions can run 20+ minutes | SSE connection reliability needed |
| Frontend security | Cannot expose Application Insights credentials to browser |
| Demo deadline: December 8, 2025 | Solution must be implementable quickly |

### Existing Environment

- All agents already export traces to Application Insights via OpenTelemetry
- Connection string available from Foundry: `project_client.telemetry.get_application_insights_connection_string()`
- SSE infrastructure already exists in orchestrator
- `operation_Id` correlation available via W3C Trace Context

---

## 2. Decision Statement

**Use OpenTelemetry + Application Insights as the source of truth for agent observability, with the Research Orchestrator backend polling App Insights and streaming filtered traces to the frontend via SSE.**

The orchestrator:
1. Assigns a unique `operation_Id` (trace ID) to each research session
2. Propagates trace context to all subagent invocations
3. Polls Application Insights via Azure Monitor Query SDK for traces matching the session's `operation_Id`
4. Streams new trace events to the frontend via the existing SSE connection

---

## 3. Specification by Example Snapshot

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Subagent tool call visibility | Research session started with `operation_Id=abc123` | `market-analyst` calls `mcp-scratchpad.add_note()` | Within 5s, SSE emits `{type: "trace", span: "add_note", agent: "market-analyst"}` |
| Session isolation | Two concurrent sessions with different `operation_Id` | Both poll App Insights | Each session receives only its own traces |
| Orchestrator-level visibility | Orchestrator delegates to `location-scout` | Span `delegate_to_location-scout` ends | SSE emits `{type: "agent_completed", agent: "location-scout", duration_ms: 2500}` |

---

## 4. Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Direct OTEL to App Insights + Backend Polling (SELECTED)** | Orchestrator polls App Insights via Azure Monitor Query SDK, streams to frontend via SSE | Native Foundry integration; full tracing in Azure Portal; subagent tool calls visible; no extra infrastructure | 2-5s latency (App Insights ingestion); polling overhead |
| **B. OTEL Collector Hub** | Deploy OTEL Collector (Container Apps) as intermediary; export to App Insights + custom real-time sink | Centralized collection; can buffer/filter; export to multiple backends | Extra infrastructure to manage; still has ingestion latency |
| **C. Custom Real-time Trace Store** | Dual export: immediate WebSocket to custom store + async App Insights | True real-time (milliseconds); full control | More code to maintain; duplicate data paths; WebSocket complexity |
| **D. Accept Limitation** | Only show orchestrator-level events; skip subagent tool visibility | Simple; no changes needed | Poor demo experience; "black box" subagents |
| **E. Wrap MCP Tools** | Create orchestrator-level wrapper that intercepts all MCP calls | Could work for orchestrator-injected tools | Doesn't capture Foundry-hosted agent tool calls; adds latency |

---

## 5. Decision Drivers

1. **Demo visibility** - Audience must see subagent tool calls in real-time
2. **Azure-native** - Use existing App Insights investment; leverage Foundry's built-in tracing
3. **Session isolation** - `operation_Id` provides natural correlation key
4. **Frontend security** - No secrets in browser; backend acts as secure proxy
5. **Implementation timeline** - Must ship by December 8, 2025
6. **SSE reliability** - Existing SSE pattern works well; heartbeats handle 20-minute sessions

---

## 6. Consequences

### Positive Outcomes
- Full visibility into subagent tool calls via App Insights traces
- Unified observability: same traces visible in Azure Portal and Research UI
- Natural session correlation via `operation_Id` (W3C trace ID)
- No additional infrastructure beyond existing App Insights
- Reuses existing SSE connection pattern

### Trade-offs / Risks
- **2-5 second latency**: App Insights has ingestion delay; events won't appear instantly
- **Polling overhead**: Backend polls App Insights every 2 seconds per active session
- **Trace context propagation dependency**: Requires Foundry to propagate `operation_Id` to hosted agents (to be verified)

### Operational Impacts
- **Costs**: Increased App Insights queries; monitor query costs
- **Monitoring**: Add dashboard for polling latency and query success rate
- **Testing**: Need integration tests for trace propagation and query filtering

---

## 7. Implementation Plan

### Phase 1: Trace Context Propagation (Day 1-2)
- [ ] Verify Foundry propagates `operation_Id` to hosted agents
- [ ] Add custom spans for orchestrator-level events (`delegate_to_*`, `agent_completed`)
- [ ] Tag spans with `gen_ai.agent.name`, `session.id`

### Phase 2: App Insights Query Integration (Day 2-3)
- [ ] Add `azure-monitor-query` dependency
- [ ] Implement `AppInsightsTracePoller` class
- [ ] Create KQL queries for session-filtered traces

### Phase 3: SSE Integration (Day 3-4)
- [ ] Add new SSE event types: `trace_span_started`, `trace_span_completed`
- [ ] Integrate poller with existing event bus
- [ ] Add heartbeat mechanism for long sessions

### Phase 4: Frontend Updates (Day 4-5)
- [ ] Update store to handle trace events
- [ ] Add trace timeline component
- [ ] Test end-to-end flow

### Telemetry/Metrics to Monitor
| Metric | Target | Alert |
|--------|--------|-------|
| `appinsights_poll_latency_ms` | < 1000ms | > 2000ms |
| `appinsights_poll_success_rate` | > 99% | < 95% |
| `trace_event_latency_ms` | < 5000ms | > 10000ms |
| `active_polling_sessions` | < 50 | > 100 |

### Owners
- Backend integration: Platform Team
- Frontend updates: Frontend Team
- Trace instrumentation: Platform Team

---

## 8. Verification

### Tests That Prove the Decision Works
1. **Integration test**: Start research session → verify `operation_Id` appears in App Insights within 10s
2. **Correlation test**: Invoke hosted agent → verify tool call spans share parent `operation_Id`
3. **SSE delivery test**: Inject trace event → verify frontend receives within 6s (5s polling + 1s buffer)
4. **Session isolation test**: Run 2 concurrent sessions → verify no cross-session trace leakage

### Rollback Plan
If trace propagation doesn't work or latency is unacceptable:
1. Revert to showing only orchestrator-level events (Option D)
2. Add "View full trace in Azure Portal" link for detailed tool call visibility
3. Document limitation for demo presenters

---

## 9. Follow-up Actions

- [ ] **ADR-006**: Consider OTEL Collector for production (if polling becomes bottleneck)
- [ ] **Documentation**: Update `OBSERVABILITY.md` with trace polling architecture
- [ ] **Documentation**: Update `specs/services/agent-research-orchestrator/ARCHITECTURE.md` with App Insights integration

---

## 10. Change Log

| Date | Author | Update |
|------|--------|--------|
| 2025-12-01 | Platform Team | Initial ADR created |
