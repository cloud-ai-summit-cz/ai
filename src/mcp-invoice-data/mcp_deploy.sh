#!/bin/bash
# Deploy MCP Invoice Data server to Azure Container Apps
# Usage: ./mcp_deploy.sh

set -e

# Configuration
RESOURCE_GROUP="rg-mcp-demo"
ACR_NAME="acrmcpsimple30456"
IMAGE_NAME="mcp-invoice-data"
CONTAINER_APP_NAME="mcp-invoice-data"
ENVIRONMENT_NAME="mcp-env"
TARGET_PORT="8014"

echo "🔐 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME --resource-group $RESOURCE_GROUP

# Generate unique image tag with timestamp and random number
IMAGE_TAG="v$(date +%Y%m%d%H%M%S)-$RANDOM"
echo "📦 Using image tag: $IMAGE_TAG"

echo "🏗️  Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG .

echo "📤 Pushing image to ACR..."
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

echo "🚀 Updating Container App..."
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

echo "✅ Deployment complete!"
echo "🌐 URL: https://$CONTAINER_APP_NAME.bluetree-fdff5920.eastus2.azurecontainerapps.io/"

# Wait and test health endpoint
echo "⏳ Waiting for container to start..."
sleep 15
echo "🏥 Health check:"
curl -s https://$CONTAINER_APP_NAME.bluetree-fdff5920.eastus2.azurecontainerapps.io/health
echo ""
