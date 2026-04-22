# Service Runbooks: agent-market-analyst

Operational procedures for Foundry Native agent.

## Common Issues

### Agent Not Responding

**Diagnosis**:
1. Check agent exists: `az cognitiveservices agent list`
2. Check MCP server connectivity

**Mitigation**:
- Re-provision agent: `uv run python -m agents.provision create`

### Wrong Output

**Diagnosis**:
1. Check prompt in agent definition
2. Check MCP server data

**Mitigation**:
- Update prompt and re-provision
