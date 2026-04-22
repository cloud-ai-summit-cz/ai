# Service Observability: agent-finance-analyst

Observability for the A2A agent.

## Metrics

| Metric | Purpose | Target | Dashboard |
|--------|---------|--------|-----------|
| `a2a_requests_total` | Request count | N/A | Agent dashboard |
| `a2a_request_duration_seconds` | A2A latency | p95 < 500ms | Agent dashboard |
| `agent_execution_duration_seconds` | Agent time | p95 < 60s | Agent dashboard |
| `mcp_call_duration_seconds` | MCP latency | p95 < 5s | Agent dashboard |
| `auth_failures_total` | Auth errors | 0 | Security dashboard |

## Logs

### Structured Log Format
```json
{
  "timestamp": "2025-11-27T10:05:30.123Z",
  "level": "INFO",
  "service": "agent-finance-analyst",
  "trace_id": "abc123",
  "a2a_task_id": "task-123",
  "message": "Financial projection completed",
  "city": "Vienna",
  "duration_ms": 25000
}
```

## Traces

### Key Spans
| Span Name | Attributes | Parent |
|-----------|------------|--------|
| `a2a.task` | task_id, caller | root |
| `agent.execute` | agent_name | a2a.task |
| `mcp.call` | tool_name, server | agent.execute |
| `llm.completion` | model, tokens | agent.execute |

## Alerts

| Alert | Condition | Severity | Channel | Runbook |
|-------|-----------|----------|---------|---------|
| A2AHighLatency | p95 > 1s | P3 | Slack | RUNBOOKS.md |
| AgentFailure | errors > 10% | P2 | Slack | RUNBOOKS.md |
| AuthFailures | >5 in 5min | P1 | Slack | RUNBOOKS.md |
