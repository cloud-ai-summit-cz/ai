# Service Deployment: agent-finance-analyst

Deployment procedures for the MAF-based A2A agent.

## Pipelines

### CI Stages
1. **Lint**: `ruff check`, `ruff format --check`
2. **Type Check**: `pyright`
3. **Unit Tests**: `pytest tests/unit`
4. **Integration Tests**: `pytest tests/integration`
5. **A2A Contract Tests**: Validate A2A protocol compliance
6. **Security Scan**: `pip-audit`, container scan

### CD Stages
1. **Build**: Docker image build
2. **Push**: Push to Azure Container Registry
3. **Deploy**: Update Container App revision
4. **Smoke Test**: A2A health check
5. **Contract Verify**: A2A protocol validation

## Environments

| Environment | Branch/Artifact | Purpose | Approvals |
|-------------|-----------------|---------|-----------|
| Local | feature/* | Development | None |
| Dev | main | Integration testing | Auto |
| Production | release/* | Live demo | Manual |

## Release Steps

### Preconditions
- [ ] All CI checks pass
- [ ] A2A contract tests pass
- [ ] Integration tests with mocked orchestrator pass

### Deployment Procedure

1. **Build container image**:
   ```bash
   docker build -t cofilotacr.azurecr.io/agent-finance-analyst:v{version} .
   docker push cofilotacr.azurecr.io/agent-finance-analyst:v{version}
   ```

2. **Update Container App**:
   ```bash
   az containerapp update \
     --name agent-finance-analyst \
     --resource-group cofilot-rg \
     --image cofilotacr.azurecr.io/agent-finance-analyst:v{version}
   ```

3. **Verify A2A endpoint**:
   ```bash
   curl -X GET https://finance-analyst.cofilot.internal/.well-known/agent.json
   ```

### Verification & Rollback

```bash
# Rollback
az containerapp revision activate \
  --name agent-finance-analyst \
  --resource-group cofilot-rg \
  --revision {previous-revision}
```

## Infrastructure

### Container App Configuration

```yaml
name: agent-finance-analyst
location: westeurope
properties:
  configuration:
    ingress:
      external: false  # Internal only
      targetPort: 8000
      transport: http
    secrets:
      - name: azure-openai-endpoint
        keyVaultUrl: https://cofilot-kv.vault.azure.net/secrets/azure-openai-endpoint
  template:
    containers:
      - name: finance-analyst
        image: cofilotacr.azurecr.io/agent-finance-analyst:latest
        resources:
          cpu: 1.0
          memory: 2Gi
        env:
          - name: AZURE_OPENAI_ENDPOINT
            secretRef: azure-openai-endpoint
          - name: MCP_SCRATCHPAD_URL
            value: http://mcp-scratchpad
          - name: MCP_FINANCE_URL
            value: http://mcp-finance
    scale:
      minReplicas: 1
      maxReplicas: 3
```

### A2A Connection in Foundry

To enable orchestrator to call this agent via A2A, create a connection in Foundry:

```bash
# Using Azure CLI / REST API
curl --request PUT \
  --url 'https://westeurope.management.azure.com/subscriptions/{sub}/resourcegroups/{rg}/providers/Microsoft.CognitiveServices/accounts/{account}/projects/{project}/connections/finance-analyst-a2a?api-version=2025-04-01-preview' \
  --header 'Authorization: Bearer {token}' \
  --header 'Content-Type: application/json' \
  --data '{
    "properties": {
      "authType": "ProjectManagedIdentity",
      "group": "ServicesAndApps",
      "category": "RemoteA2A",
      "target": "https://agent-finance-analyst.internal.cofilot.westeurope.azurecontainerapps.io",
      "isSharedToAll": true,
      "audience": "api://agent-finance-analyst"
    }
  }'
```

### Required Azure Resources
- Azure Container Apps Environment (internal)
- Azure Container Registry
- Azure Key Vault
- Azure Managed Identity
- Azure AI Foundry connection (for A2A)

### IaC Reference
- Terraform: `infra/services/agent-finance-analyst.tf`
