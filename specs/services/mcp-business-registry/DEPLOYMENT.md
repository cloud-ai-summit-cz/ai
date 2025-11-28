# Service Deployment: mcp-business-registry

## Container Specification

```yaml
name: mcp-business-registry
image: ${ACR_NAME}.azurecr.io/mcp-business-registry:${VERSION}
resources:
  cpu: 0.5
  memory: 1Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-business-registry \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-business-registry:${VERSION}
```
