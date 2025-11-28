# Service Observability: agent-market-analyst

Observability for Foundry Native agent.

## Metrics

Foundry-managed metrics via connected Application Insights:
- Agent invocation count
- Agent execution duration
- Tool call latency

## Traces

Traces exported to Foundry-connected Application Insights.

## Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| AgentFailure | >20% errors | P2 |
