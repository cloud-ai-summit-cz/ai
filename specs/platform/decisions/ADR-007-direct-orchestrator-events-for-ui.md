# ADR-007: Direct Orchestrator Events for UI (Reverting from Trace-Based SSE)

## Status
**Accepted** - 2025-01-XX

## Context

In ADR-005, we implemented trace-based SSE events for the UI, polling Azure Application Insights for OpenTelemetry spans to provide real-time visibility into agent operations. This approach was chosen because:
- Azure AI Foundry Agent Service executes tools server-side
- Direct interception from the orchestrator was assumed to be difficult
- App Insights provides a unified view of distributed traces

However, after implementing ADR-006 (MCP tools in orchestrator), we discovered:

1. **Latency Issues**: App Insights has 2-5 second ingestion delay, making "real-time" events noticeably delayed for UI updates.

2. **MCP Tools Now in Orchestrator**: ADR-006 moved MCP tool calls into the MAF orchestrator with middleware interception. This means we already have direct, real-time access to tool calls.

3. **Complexity**: The trace polling approach added significant complexity:
   - `trace_poller.py` (~450 lines) with KQL queries
   - Complex async task management in `api.py` event generator
   - Duplicate event types (trace-based + legacy)
   - Session/operation ID correlation challenges

4. **Reliability**: Trace events depend on App Insights availability and ingestion timing, adding a fragile dependency for UI functionality.

## Decision

**Revert to direct orchestrator-generated events for UI SSE streaming.**

- **Keep** OpenTelemetry traces for observability (dashboards, debugging, APM)
- **Remove** trace polling from SSE event generator for UI
- **Use** direct events from orchestrator middleware as the primary source

### Event Source Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Orchestrator  │─────▶│   SSE Stream    │─────▶│       UI        │
│   (middleware)  │      │   (api.py)      │      │   (store.ts)    │
└────────┬────────┘      └─────────────────┘      └─────────────────┘
         │
         │ (parallel, for observability only)
         ▼
┌─────────────────┐      ┌─────────────────┐
│  OpenTelemetry  │─────▶│  App Insights   │ ◀── Dashboards, debugging
│     Tracer      │      │   (traces)      │
└─────────────────┘      └─────────────────┘
```

### Primary SSE Events (from orchestrator)

| Event Type | Source | Purpose |
|------------|--------|---------|
| `workflow_started` | Orchestrator | Workflow initialization |
| `workflow_completed` | Orchestrator | Workflow completion |
| `workflow_failed` | Orchestrator | Workflow failure |
| `agent_started` | Orchestrator | Subagent invocation started |
| `agent_completed` | Orchestrator | Subagent invocation completed |
| `agent_response` | Orchestrator | Subagent response with preview |
| `tool_call_started` | Middleware | Tool call initiated |
| `tool_call_completed` | Middleware | Tool call completed with results |
| `tool_call_failed` | Middleware | Tool call error |
| `scratchpad_updated` | Middleware | Scratchpad write operation |
| `subagent_tool_started` | Stream callback | Subagent's tool call started |
| `subagent_tool_completed` | Stream callback | Subagent's tool call completed |
| `synthesis_completed` | Orchestrator | Final report ready |

### Deprecated Events (observability only)

| Event Type | Status |
|------------|--------|
| `trace_span_started` | Removed from UI SSE |
| `trace_span_completed` | Removed from UI SSE |
| `trace_tool_call` | Removed from UI SSE |

These trace events remain in the codebase for potential future use but are not emitted to the UI SSE stream.

## Consequences

### Positive
- **Real-time events**: No 2-5 second delay from App Insights ingestion
- **Reduced complexity**: Remove trace_poller.py dependency from SSE streaming
- **Improved reliability**: UI events don't depend on App Insights availability
- **Simpler debugging**: Direct correlation between orchestrator actions and UI updates
- **Lower latency**: Events emitted immediately when tool calls occur

### Negative
- **Less unified observability**: UI events and traces are now separate paths
- **Trace events unused**: `trace_poller.py` code becomes dormant (but kept for observability tools)

### Neutral
- **Frontend unchanged**: `store.ts` already handles both trace and legacy events
- **Observability intact**: OpenTelemetry traces continue to flow to App Insights

## Implementation

1. **api.py**: Remove trace polling from `event_generator()`, emit only workflow events from orchestrator
2. **sse-events.yaml**: Update contract to show direct events as primary
3. **models.py**: Remove "Legacy" comments from direct event types
4. **trace_poller.py**: Keep for potential future use but remove from SSE flow
5. **store.ts**: No changes needed (already handles direct events)

## Related Documents
- ADR-005: Real-time Agent Observability (trace-based approach - partially superseded)
- ADR-006: MCP Tools in Orchestrator (enabled direct middleware interception)
- `specs/services/agent-research-orchestrator/contracts/sse-events.yaml`
