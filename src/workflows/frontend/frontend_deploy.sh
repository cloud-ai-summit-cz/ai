#!/usr/bin/env bash
set -euo pipefail

# Deploy the static frontend to Azure Static Web Apps using SWA CLI.
# Prereqs: az login, SWA CLI installed (`npm i -g @azure/static-web-apps-cli`).

RESOURCE_GROUP="rg-mcp-demo"
SWA_NAME="cai-invoice-workflow-demo"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SRC="${SCRIPT_DIR}"
PARENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Retrieving deployment token for ${SWA_NAME}..." >&2
DEPLOY_TOKEN="$(az staticwebapp secrets list -g "$RESOURCE_GROUP" -n "$SWA_NAME" --query "properties.apiKey" -o tsv)"

if [[ -z "${DEPLOY_TOKEN}" ]]; then
  echo "Failed to retrieve deployment token" >&2
  exit 1
fi

export SWA_CLI_DEPLOYMENT_TOKEN="${DEPLOY_TOKEN}"

echo "Deploying from ${APP_SRC} using swa CLI (running in ${PARENT_DIR})..." >&2
pushd "${PARENT_DIR}" >/dev/null
swa deploy "./frontend" --env production
popd >/dev/null

echo "Deploy complete. Verify at https://${SWA_NAME}.azurestaticapps.net"