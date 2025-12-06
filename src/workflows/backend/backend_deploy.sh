#!/bin/bash
# Deploy Invoice Workflow backend to Azure Container Apps via ACR remote build
# Usage: ./backend_deploy.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env if present (keeps .env values available for defaults below)
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -o allexport
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/.env"
  set +o allexport
fi

# Configuration
RESOURCE_GROUP="rg-mcp-demo"
ACR_NAME="acrmcpsimple30456"
IMAGE_NAME="mcp-invoice-backend"
CONTAINER_APP_NAME="be-invoice-demo"
ENVIRONMENT_NAME="mcp-env"
TARGET_PORT="8000"
AZURE_AI_ENDPOINT="${AZURE_AI_ENDPOINT:-}" # required

if [[ -z "$AZURE_AI_ENDPOINT" ]]; then
  echo "AZURE_AI_ENDPOINT is required (e.g., https://ai-foundry-<region>.services.ai.azure.com/api/projects/<project-name>)." >&2
  exit 1
fi

IMAGE_TAG="v$(date +%Y%m%d%H%M%S)-$RANDOM"
echo "Using image tag: $IMAGE_TAG"

echo "Building image in ACR (remote build)..."
az acr build \
  --registry "$ACR_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG" \
  --platform linux/amd64 \
  --file Dockerfile \
  .

echo "Updating Container App..."
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG" \
  --set-env-vars "AZURE_AI_ENDPOINT=$AZURE_AI_ENDPOINT" \

APP_FQDN=$(az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Deployment complete."
echo "URL: https://$APP_FQDN/"

echo "Waiting for container to start..."
sleep 15

echo "Health check:"
curl -s "https://$APP_FQDN/health" || true
echo ""
