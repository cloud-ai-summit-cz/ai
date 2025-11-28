# Service Runbooks: agent-research-orchestrator

Operational procedures for maintaining the research orchestrator in production.

## On-Call Quick Reference

- **Dashboards**: [App Insights - Orchestrator](https://portal.azure.com/#view/AppInsights)
- **Logs**: `ContainerAppConsoleLogs | where ContainerAppName == "agent-research-orchestrator"`
- **Alerts**: Slack #cofilot-alerts

## Common Incidents

### High Error Rate

**Alert**: `HighErrorRate` - error_rate > 10% for 5m

**Symptoms**:
- Users report failed research sessions
- Error rate spike in dashboard

**Diagnosis**:
1. Check container logs for error patterns:
   ```kusto
   ContainerAppConsoleLogs
   | where ContainerAppName == "agent-research-orchestrator"
   | where Log contains "ERROR"
   | summarize count() by bin(TimeGenerated, 1m)
   ```
2. Check downstream agent health
3. Check MCP server availability
4. Check Azure OpenAI quota

**Mitigation**:
- [ ] If agent failures: Check specific agent logs
- [ ] If MCP failures: Restart MCP containers
- [ ] If OpenAI quota: Wait for reset or request increase
- [ ] If container crash: Check memory/CPU, scale up

### High Latency

**Alert**: `HighLatency` - p95 > 500ms for 5m

**Symptoms**:
- Slow API responses
- SSE events delayed

**Diagnosis**:
1. Check which component is slow:
   ```kusto
   dependencies
   | where cloud_RoleName == "agent-research-orchestrator"
   | summarize avg(duration) by target
   ```
2. Check Azure OpenAI latency
3. Check agent invocation times

**Mitigation**:
- [ ] If OpenAI slow: Check service status, consider model switch
- [ ] If agent slow: Check specific agent container
- [ ] If CPU high: Scale out container replicas
- [ ] If network: Check Container Apps environment

### Workflow Timeout

**Alert**: `WorkflowTimeout` - workflow_duration > 5m

**Symptoms**:
- Research sessions stuck in "running"
- No completion events

**Diagnosis**:
1. Check current session state:
   ```bash
   curl https://orchestrator.cofilot.demo/research/sessions/{id}
   ```
2. Check which agent is stuck
3. Check scratchpad for partial results

**Mitigation**:
- [ ] If agent stuck: Restart agent container
- [ ] If deadlock: Cancel session, retry
- [ ] If systematic: Check for A2A connectivity issues

### Agent Failure

**Alert**: `AgentFailure` - agent_errors > 5 in 1m

**Symptoms**:
- Specific agent consistently failing
- Partial research results

**Diagnosis**:
1. Identify failing agent from logs
2. Check agent-specific logs
3. Check MCP server the agent uses

**Mitigation**:
- [ ] If Foundry agent: Check AI Foundry portal status
- [ ] If Hosted agent: Check container health, restart
- [ ] If A2A agent: Check network, auth tokens
- [ ] If MCP issue: Restart MCP server

### No Traffic

**Alert**: `NoTraffic` - requests = 0 for 10m

**Symptoms**:
- No requests in metrics
- Frontend may be down

**Diagnosis**:
1. Check container health
2. Check ingress configuration
3. Check DNS resolution
4. Check frontend status

**Mitigation**:
- [ ] If container down: Restart container app
- [ ] If ingress issue: Check Container Apps Environment
- [ ] If DNS: Check custom domain configuration

## Maintenance Tasks

### Rotating Secrets

1. Generate new secret in Key Vault
2. Create new secret version
3. Restart container app to pick up new secret:
   ```bash
   az containerapp revision restart \
     --name agent-research-orchestrator \
     --resource-group cofilot-rg
   ```

### Scaling

**Manual scale up**:
```bash
az containerapp update \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg \
  --min-replicas 2 \
  --max-replicas 5
```

**Check current scale**:
```bash
az containerapp replica list \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg
```

### Deployment Rollback

```bash
# List revisions
az containerapp revision list \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg

# Activate previous revision
az containerapp revision activate \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg \
  --revision agent-research-orchestrator--{revision-id}

# Shift traffic
az containerapp ingress traffic set \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg \
  --revision-weight agent-research-orchestrator--{revision-id}=100
```

### Log Investigation

```kusto
// Recent errors
ContainerAppConsoleLogs
| where ContainerAppName == "agent-research-orchestrator"
| where TimeGenerated > ago(1h)
| where Log contains "ERROR"
| project TimeGenerated, Log

// Session trace
ContainerAppConsoleLogs
| where ContainerAppName == "agent-research-orchestrator"
| where Log contains "session_id=550e8400"
| project TimeGenerated, Log
| order by TimeGenerated asc
```
