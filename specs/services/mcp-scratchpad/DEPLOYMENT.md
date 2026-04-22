# Service Deployment: mcp-scratchpad

## Container Specification

```yaml
name: mcp-scratchpad
image: ${ACR_NAME}.azurecr.io/mcp-scratchpad:${VERSION}
resources:
  cpu: 0.5
  memory: 1Gi
env:
  - name: COSMOS_ENDPOINT
    secretRef: cosmos-endpoint
  - name: AZURE_CLIENT_ID
    value: ${MANAGED_IDENTITY_CLIENT_ID}
```

## Deployment Steps

```bash
# Build and push
docker build -t ${ACR_NAME}.azurecr.io/mcp-scratchpad:${VERSION} .
docker push ${ACR_NAME}.azurecr.io/mcp-scratchpad:${VERSION}

# Deploy to Container Apps
az containerapp update \
  --name mcp-scratchpad \
  --resource-group ${RG_NAME} \
  --image ${ACR_NAME}.azurecr.io/mcp-scratchpad:${VERSION}
```

## Health Check
- Endpoint: `GET /health`
- Expected: `200 OK`
