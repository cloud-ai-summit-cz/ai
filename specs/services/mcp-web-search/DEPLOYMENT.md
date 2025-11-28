# Service Deployment: mcp-web-search

## Container Specification

```yaml
name: mcp-web-search
image: ${ACR_NAME}.azurecr.io/mcp-web-search:${VERSION}
resources:
  cpu: 0.5
  memory: 1Gi
```

## Deployment
```bash
az containerapp update \
  --name mcp-web-search \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-web-search:${VERSION}
```

## Health Check
- Endpoint: `GET /health`
- Expected: `200 OK`
