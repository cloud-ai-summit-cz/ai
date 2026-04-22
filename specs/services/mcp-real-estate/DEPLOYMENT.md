# Service Deployment: mcp-real-estate

## Container Specification

```yaml
name: mcp-real-estate
image: ${ACR_NAME}.azurecr.io/mcp-real-estate:${VERSION}
resources:
  cpu: 0.25
  memory: 0.5Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-real-estate \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-real-estate:${VERSION}
```
