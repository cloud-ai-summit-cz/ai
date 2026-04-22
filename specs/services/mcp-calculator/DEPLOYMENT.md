# Service Deployment: mcp-calculator

## Container Specification

```yaml
name: mcp-calculator
image: ${ACR_NAME}.azurecr.io/mcp-calculator:${VERSION}
resources:
  cpu: 0.25
  memory: 0.5Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-calculator \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-calculator:${VERSION}
```
