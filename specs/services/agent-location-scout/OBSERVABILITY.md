# Service Observability: agent-location-scout

Observability for the LangGraph Hosted Agent.

## Metrics

| Metric | Purpose | Target | Dashboard |
|--------|---------|--------|-----------|
| `agent_invocation_total` | Invocation count | N/A | Agent dashboard |
| `agent_invocation_duration_seconds` | Execution time | p95 < 30s | Agent dashboard |
| `agent_invocation_errors_total` | Failure count | < 5% | Agent dashboard |
| `mcp_call_duration_seconds` | MCP tool latency | p95 < 5s | Agent dashboard |

## Logs

### Structured Log Format
```json
{
  "timestamp": "2025-11-27T10:05:30.123Z",
  "level": "INFO",
  "service": "agent-location-scout",
  "trace_id": "abc123",
  "message": "Location analysis completed",
  "city": "Vienna",
  "neighborhoods_analyzed": 5,
  "duration_ms": 15000
}
```

### Logging via Hosting Adapter
The `azure-ai-agentserver-langgraph` adapter provides:
- Automatic OpenTelemetry setup
- Azure Monitor integration
- Structured logging to connected Application Insights

## Traces

### Key Spans
| Span Name | Attributes | Parent |
|-----------|------------|--------|
| `agent.invoke` | agent_name, framework | Foundry request |
| `langgraph.node` | node_name | agent.invoke |
| `mcp.call` | tool_name, server | langgraph.node |
| `llm.completion` | model, tokens | langgraph.node |

### Trace Export
- Traces exported to Foundry-connected Application Insights
- Can also export to custom OTEL endpoint via `OTEL_EXPORTER_ENDPOINT`

## Alerts

| Alert | Condition | Severity | Channel | Runbook |
|-------|-----------|----------|---------|---------|
| AgentHighLatency | p95 > 60s | P3 | Slack | RUNBOOKS.md#high-latency |
| AgentFailures | errors > 20% | P2 | Slack | RUNBOOKS.md#agent-failure |

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Successful analysis | Valid city | Agent invoked | Trace with all spans visible |
| MCP failure | MCP server down | Tool called | Error logged with retry info |
