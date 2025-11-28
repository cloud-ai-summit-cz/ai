# Service Runbooks: agent-location-scout

Operational procedures for the LangGraph Hosted Agent.

## On-Call Quick Reference

- **Foundry Portal**: [Agent Management](https://ai.azure.com)
- **Logs**: Application Insights connected to Foundry project
- **CLI**: `az cognitiveservices agent`

## Common Incidents

### Agent Not Responding

**Symptoms**:
- Orchestrator gets timeout on Responses API
- Agent status shows "Stopped" or "Failed"

**Diagnosis**:
1. Check agent status:
   ```bash
   az cognitiveservices agent show \
     --account-name cofilot-foundry \
     --project-name cofilot-project \
     --name location-scout
   ```
2. Check deployment logs in Foundry portal

**Mitigation**:
- [ ] If stopped: Start agent
- [ ] If failed: Check logs, redeploy

### High Latency

**Symptoms**:
- Agent responses taking >60s

**Diagnosis**:
1. Check MCP server latency
2. Check Azure OpenAI latency
3. Check agent traces in App Insights

**Mitigation**:
- [ ] If MCP slow: Scale MCP servers
- [ ] If OpenAI slow: Check service status

### Agent Failure

**Symptoms**:
- Responses API returns errors

**Diagnosis**:
1. Check agent logs in Foundry portal
2. Check container health

**Mitigation**:
- [ ] Restart agent deployment
- [ ] If persistent: Rollback to previous version

## Maintenance Tasks

### Updating Agent

```bash
# Build and push new image
docker build -t cofilotacr.azurecr.io/agent-location-scout:v2 .
docker push cofilotacr.azurecr.io/agent-location-scout:v2

# Create new version (creates new deployment)
# Use SDK as shown in DEPLOYMENT.md
```

### Scaling

```bash
# Update replicas
az cognitiveservices agent update \
  --account-name cofilot-foundry \
  --project-name cofilot-project \
  --name location-scout \
  --agent-version 1 \
  --min-replicas 1 \
  --max-replicas 3
```

### Rollback

```bash
# Stop current
az cognitiveservices agent stop \
  --account-name cofilot-foundry \
  --project-name cofilot-project \
  --name location-scout \
  --agent-version 2

# Start previous
az cognitiveservices agent start \
  --account-name cofilot-foundry \
  --project-name cofilot-project \
  --name location-scout \
  --agent-version 1
```
