# Service Runbooks: web-research

## On-Call Quick Reference
- **Logs**: Azure Portal -> Container Apps -> Logs
- **Metrics**: Azure Portal -> Application Insights

## Common Incidents

### White Screen of Death (WSOD)
**Symptoms**:
- User sees blank page.
- Console shows "Uncaught TypeError".

**Diagnosis**:
1. Check browser console for stack trace.
2. Verify if a recent deployment introduced a breaking change.
3. Check if `config.js` loaded correctly (network tab).

**Mitigation**:
- [ ] Rollback to previous container image revision.
- [ ] Fix bug and hotfix.

### SSE Not Connecting
**Symptoms**:
- "Connecting..." spinner persists.
- Console shows `EventSource failed`.

**Diagnosis**:
1. Check if `agent-research-orchestrator` is running.
2. Verify CORS settings on the backend.
3. Check if corporate firewall/VPN blocks SSE (EventStream).

**Mitigation**:
- [ ] Restart backend service.
- [ ] Advise user to check network connection.

## Maintenance Tasks

### Updating Configuration
1. Update environment variables in Azure Container App revision.
2. New revision will automatically generate new `config.js` on startup.
