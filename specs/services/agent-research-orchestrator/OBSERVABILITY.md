# Service Observability: agent-research-orchestrator

Metrics, logs, and traces for monitoring the research orchestrator.

## Metrics

| Metric | Purpose | Target | Dashboard |
|--------|---------|--------|-----------|
| `http_requests_total` | Request volume | N/A | Main dashboard |
| `http_request_duration_seconds` | API latency | p95 < 200ms | Main dashboard |
| `agent_invocation_duration_seconds` | Agent call latency | p95 < 30s | Agent dashboard |
| `agent_invocation_total` | Agent call volume | N/A | Agent dashboard |
| `agent_invocation_errors_total` | Agent failures | < 5% | Agent dashboard |
| `workflow_duration_seconds` | End-to-end workflow | p95 < 180s | Main dashboard |
| `active_sessions` | Concurrent sessions | < 100 | Main dashboard |
| `sse_connections_active` | Active SSE streams | < 200 | Main dashboard |
| `appinsights_poll_latency_ms` | App Insights query latency | p95 < 1000ms | Trace dashboard |
| `appinsights_poll_success_rate` | Query success rate | > 99% | Trace dashboard |
| `trace_event_latency_ms` | Time from agent action to SSE | p95 < 8000ms | Trace dashboard |
| `active_polling_sessions` | Sessions with active trace polling | < 50 | Trace dashboard |

## Logs

### Structured Log Format
```json
{
  "timestamp": "2025-11-27T10:05:30.123Z",
  "level": "INFO",
  "service": "agent-research-orchestrator",
  "trace_id": "abc123",
  "span_id": "def456",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Agent invocation completed",
  "agent": "market-analyst",
  "duration_ms": 2500,
  "status": "success"
}
```

### Log Fields
| Field | Type | Description | PII |
|-------|------|-------------|-----|
| timestamp | ISO 8601 | Event time | No |
| level | string | DEBUG/INFO/WARNING/ERROR | No |
| trace_id | string | Distributed trace ID | No |
| session_id | UUID | Research session | No |
| agent | string | Agent name | No |
| duration_ms | int | Operation duration | No |
| query | string | Research question (truncated) | No* |

*Demo data only, no real PII

### Sampling Strategy
- ERROR logs: 100% sampled
- WARNING logs: 100% sampled
- INFO logs: 100% sampled (low volume expected)
- DEBUG logs: 10% sampled in production

## Traces

### Key Spans
| Span Name | Attributes | Parent |
|-----------|------------|--------|
| `POST /research/sessions` | session_id | root |
| `research_session` | session_id, research.query | root (provides operation_Id for entire session) |
| `workflow.execute` | session_id, phase | research_session |
| `delegate_to_{agent}` | agent_name, gen_ai.agent.name | workflow |
| `agent.invoke` | agent_name, agent_type | delegate_to_* |
| `mcp.call` | tool_name, server | agent.invoke |
| `a2a.request` | target_url | agent.invoke |

### Application Insights Trace Polling (ADR-005)

The orchestrator polls Application Insights for traces to provide real-time visibility into subagent tool calls. See `specs/platform/decisions/ADR-005-realtime-agent-observability.md`.

#### Session Correlation

Each research session is assigned a unique `operation_Id` (W3C trace ID) that correlates all spans:

```python
# Session start creates parent span
tracer = trace.get_tracer("research-orchestrator")
with tracer.start_as_current_span("research_session") as span:
    span.set_attribute("session.id", session_id)
    # All subagent invocations inherit this operation_Id
```

#### KQL Query for Session Traces

```kusto
// Query executed by trace poller every 2 seconds
union traces, dependencies
| where operation_Id == "{session_operation_id}"
| where timestamp > datetime({last_poll_timestamp})
| project timestamp, name, duration, customDimensions, success
| order by timestamp asc
```

#### SSE Events from Traces

| Event Type | Source | Payload |
|------------|--------|---------|
| `trace_span_started` | Trace Poller | `{span_name, agent_name, operation_id, timestamp}` |
| `trace_span_completed` | Trace Poller | `{span_name, agent_name, duration_ms, success}` |
| `trace_tool_call` | Trace Poller | `{tool_name, mcp_server, agent_name}` |

### Trace Attributes
```python
# Standard attributes for all spans
{
    "service.name": "agent-research-orchestrator",
    "service.version": "1.0.0",
    "deployment.environment": "production",
    "session.id": "...",
    "agent.name": "market-analyst",
    "agent.type": "foundry_native"  # foundry_native | foundry_hosted | a2a
}
```

### Sampling Configuration
- Production: 10% of successful traces, 100% of error traces
- Staging: 100% of all traces
- Development: 100% of all traces

## Alerts

| Alert | Condition | Severity | Channel | Runbook |
|-------|-----------|----------|---------|---------|
| HighErrorRate | error_rate > 10% for 5m | P2 | Slack #alerts | RUNBOOKS.md#high-error-rate |
| HighLatency | p95 > 500ms for 5m | P3 | Slack #alerts | RUNBOOKS.md#high-latency |
| WorkflowTimeout | workflow_duration > 5m | P3 | Slack #alerts | RUNBOOKS.md#workflow-timeout |
| AgentFailure | agent_errors > 5 in 1m | P2 | Slack #alerts | RUNBOOKS.md#agent-failure |
| NoTraffic | requests = 0 for 10m | P4 | Slack #alerts | RUNBOOKS.md#no-traffic |

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Latency alert fires | p95 latency > 500ms | Sustained for 5 minutes | Alert HighLatency triggers |
| Error tracking | Agent invocation fails | Within 1 second | Error logged with trace_id |
| Distributed trace | Research workflow runs | Completes | All spans visible in App Insights |
| Subagent tool visibility | Session started with operation_Id | market-analyst calls mcp-scratchpad | SSE emits trace_tool_call within 8s |
| Session trace isolation | Two concurrent sessions | Both poll App Insights | Each receives only its own traces |

## Dashboards

### Main Dashboard
- Request rate and error rate
- Latency percentiles (p50, p95, p99)
- Active sessions gauge
- Workflow completion rate

### Agent Dashboard
- Per-agent invocation counts
- Per-agent latency distribution
- Agent error rates
- A2A vs Foundry breakdown

### Trace Polling Dashboard (ADR-005)
- App Insights poll latency histogram
- Poll success rate gauge
- Active polling sessions gauge
- Trace event end-to-end latency (agent action → SSE delivery)
- Traces per session count
