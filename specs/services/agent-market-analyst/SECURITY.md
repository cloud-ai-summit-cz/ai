# Service Security: agent-market-analyst

Security for Foundry Native agent.

## Threat Model Snapshot

| Asset | Threat | Mitigation |
|-------|--------|------------|
| Agent prompt | Prompt injection | Structured prompts, input validation |
| MCP data | Unauthorized access | Internal network, no external exposure |

## Controls Checklist

### Authentication/Authorization
- [ ] Foundry-managed authentication
- [ ] MCP servers internal only

### Data Classification
| Data Type | Classification | Handling |
|-----------|----------------|----------|
| Market data | Demo/Synthetic | No retention beyond session |
