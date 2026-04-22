# Service Deployment: mcp-government-data

## Container Specification

```yaml
name: mcp-government-data
image: ${ACR_NAME}.azurecr.io/mcp-government-data:${VERSION}
resources:
  cpu: 0.25
  memory: 0.5Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-government-data \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-government-data:${VERSION}
```
