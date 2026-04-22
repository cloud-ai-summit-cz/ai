# Service Runbooks: agent-finance-analyst

Operational procedures for the A2A agent.

## On-Call Quick Reference

- **Logs**: Container Apps Console Logs
- **Metrics**: Application Insights

## Common Incidents

### A2A Authentication Failures

**Symptoms**:
- 401 errors from orchestrator
- Auth failure alerts

**Diagnosis**:
1. Check managed identity configuration
2. Verify Foundry A2A connection setup
3. Check token audience

**Mitigation**:
- [ ] Verify managed identity has correct permissions
- [ ] Re-create A2A connection in Foundry

### Agent Not Responding

**Symptoms**:
- Timeouts from orchestrator
- Container unhealthy

**Diagnosis**:
1. Check container health
2. Check container logs
3. Check MCP server availability

**Mitigation**:
- [ ] Restart container
- [ ] Check MCP servers

## Maintenance Tasks

### Updating A2A Connection

```bash
# Re-create connection if endpoint changes
az cognitiveservices account connection update ...
```

### Scaling

```bash
az containerapp update \
  --name agent-finance-analyst \
  --resource-group cofilot-rg \
  --min-replicas 2 \
  --max-replicas 5
```
