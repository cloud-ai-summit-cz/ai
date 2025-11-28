# Service Deployment: mcp-demographics

## Container Specification

```yaml
name: mcp-demographics
image: ${ACR_NAME}.azurecr.io/mcp-demographics:${VERSION}
resources:
  cpu: 0.25
  memory: 0.5Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-demographics \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-demographics:${VERSION}
```
