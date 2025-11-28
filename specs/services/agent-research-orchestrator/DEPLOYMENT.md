# Service Deployment: agent-research-orchestrator

Deployment procedures for the MAF-based research orchestrator.

## Pipelines

### CI Stages
1. **Lint**: `ruff check`, `ruff format --check`
2. **Type Check**: `pyright`
3. **Unit Tests**: `pytest tests/unit`
4. **Integration Tests**: `pytest tests/integration` (requires Azure resources)
5. **Security Scan**: `pip-audit`, container scan

### CD Stages
1. **Build**: Docker image build
2. **Push**: Push to Azure Container Registry
3. **Deploy**: Update Container App revision
4. **Smoke Test**: Health check + basic workflow test
5. **Promote**: Traffic shift (canary)

## Environments

| Environment | Branch/Artifact | Purpose | Approvals |
|-------------|-----------------|---------|-----------|
| Local | feature/* | Development | None |
| Dev | main | Integration testing | Auto |
| Staging | main + tag | Pre-production validation | Manual |
| Production | release/* | Live demo | Manual |

## Release Steps

### Preconditions
- [ ] All CI checks pass
- [ ] Integration tests pass against dev environment
- [ ] No critical security vulnerabilities

### Deployment Procedure
1. Build container image with new tag
2. Push to ACR: `cofilotacr.azurecr.io/agent-research-orchestrator:v{version}`
3. Update Container App with new image
4. Wait for health checks (30s timeout)
5. Run smoke tests
6. Shift traffic: 10% → 50% → 100%

### Verification & Rollback
- **Health endpoint**: `GET /health` returns 200
- **Smoke test**: POST /research/sessions creates session
- **Rollback**: Revert to previous Container App revision

```bash
# Rollback command
az containerapp revision activate \
  --name agent-research-orchestrator \
  --resource-group cofilot-rg \
  --revision {previous-revision}
```

## Infrastructure

### Container App Configuration

```yaml
name: agent-research-orchestrator
location: westeurope
properties:
  configuration:
    ingress:
      external: true
      targetPort: 8000
      transport: http
      corsPolicy:
        allowedOrigins: ["https://research.cofilot.demo"]
        allowedMethods: ["GET", "POST", "OPTIONS"]
        allowedHeaders: ["*"]
    secrets:
      - name: azure-openai-endpoint
        keyVaultUrl: https://cofilot-kv.vault.azure.net/secrets/azure-openai-endpoint
  template:
    containers:
      - name: orchestrator
        image: cofilotacr.azurecr.io/agent-research-orchestrator:latest
        resources:
          cpu: 1.0
          memory: 2Gi
        env:
          - name: AZURE_AI_FOUNDRY_ENDPOINT
            secretRef: foundry-endpoint
          - name: AZURE_OPENAI_ENDPOINT
            secretRef: azure-openai-endpoint
          - name: MCP_SCRATCHPAD_URL
            value: http://mcp-scratchpad
          - name: FINANCE_ANALYST_A2A_URL
            value: http://agent-finance-analyst
    scale:
      minReplicas: 1
      maxReplicas: 3
      rules:
        - name: http-scaling
          http:
            metadata:
              concurrentRequests: "50"
```

### Required Azure Resources
- Azure Container Apps Environment
- Azure Container Registry
- Azure Key Vault (secrets)
- Azure Managed Identity
- Azure AI Foundry Project (for agent access)

### IaC Reference
- Terraform: `infra/services/agent-research-orchestrator.tf`
