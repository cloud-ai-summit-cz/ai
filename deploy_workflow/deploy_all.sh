#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/azure/terraform"
AGENT_PROVISION_DIR="$SCRIPT_DIR/agent_provisioning"
FRONTEND_DIR="$ROOT_DIR/src/workflows/frontend"

echo "============================================================"
echo "Workflow Deploy (Terraform -> Agents -> Terraform)"
echo "============================================================"
echo "Terraform dir: $TERRAFORM_DIR"
echo "Agents dir:    $AGENT_PROVISION_DIR"
echo

if ! command -v terraform >/dev/null 2>&1; then
	echo "ERROR: terraform is not installed or not on PATH" >&2
	exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "ERROR: uv is not installed or not on PATH" >&2
	exit 1
fi

if [[ ! -d "$TERRAFORM_DIR" ]]; then
	echo "ERROR: Terraform directory not found: $TERRAFORM_DIR" >&2
	exit 1
fi

if [[ ! -d "$AGENT_PROVISION_DIR" ]]; then
	echo "ERROR: Agent provisioning directory not found: $AGENT_PROVISION_DIR" >&2
	exit 1
fi

echo "[1/4] Terraform apply (bootstrap_with_hello_world=true)"
(
	cd "$TERRAFORM_DIR"
	terraform init -input=false
	terraform apply -auto-approve -var="bootstrap_with_hello_world=true"
)

echo
echo "[2/4] Provision agents"

FOUNDRY_ENDPOINT=""
MCP_BASE_URL=""
SWA_NAME=""
RESOURCE_GROUP_NAME=""

(
	cd "$TERRAFORM_DIR"

	# Note: output names are defined in deploy_workflow/azure/terraform/outputs.tf
	FOUNDRY_ENDPOINT="$(terraform output -raw ai_foundry_project_endpoint 2>/dev/null || true)"
	MCP_BASE_URL="$(terraform output -raw mcp_invoice_data_url 2>/dev/null || true)"
	SWA_NAME="$(terraform output -raw static_web_app_name 2>/dev/null || true)"
	RESOURCE_GROUP_NAME="$(terraform output -raw resource_group_name 2>/dev/null || true)"

	# Export for the parent shell via printf + command substitution.
	printf "%s\n" "$FOUNDRY_ENDPOINT" >"$SCRIPT_DIR/.deploy_all_foundry_endpoint.tmp"
	printf "%s\n" "$MCP_BASE_URL" >"$SCRIPT_DIR/.deploy_all_mcp_base_url.tmp"
	printf "%s\n" "$SWA_NAME" >"$SCRIPT_DIR/.deploy_all_swa_name.tmp"
	printf "%s\n" "$RESOURCE_GROUP_NAME" >"$SCRIPT_DIR/.deploy_all_rg_name.tmp"
)

FOUNDRY_ENDPOINT="$(cat "$SCRIPT_DIR/.deploy_all_foundry_endpoint.tmp" 2>/dev/null || true)"
MCP_BASE_URL="$(cat "$SCRIPT_DIR/.deploy_all_mcp_base_url.tmp" 2>/dev/null || true)"
SWA_NAME="$(cat "$SCRIPT_DIR/.deploy_all_swa_name.tmp" 2>/dev/null || true)"
RESOURCE_GROUP_NAME="$(cat "$SCRIPT_DIR/.deploy_all_rg_name.tmp" 2>/dev/null || true)"
rm -f \
	"$SCRIPT_DIR/.deploy_all_foundry_endpoint.tmp" \
	"$SCRIPT_DIR/.deploy_all_mcp_base_url.tmp" \
	"$SCRIPT_DIR/.deploy_all_swa_name.tmp" \
	"$SCRIPT_DIR/.deploy_all_rg_name.tmp"

AGENT_ARGS=()
if [[ -n "$FOUNDRY_ENDPOINT" && "$FOUNDRY_ENDPOINT" != "null" ]]; then
	AGENT_ARGS+=("--azure-ai-foundry-endpoint" "$FOUNDRY_ENDPOINT")
else
	echo "WARN: Terraform output ai_foundry_project_endpoint not found; provisioning will rely on config/.env" >&2
fi

if [[ -n "$MCP_BASE_URL" && "$MCP_BASE_URL" != "null" ]]; then
	MCP_URL="$MCP_BASE_URL"
	if [[ "$MCP_URL" != */mcp ]]; then
		MCP_URL="$MCP_URL/mcp"
	fi
	AGENT_ARGS+=("--mcp-invoice-data-url" "$MCP_URL")
else
	echo "WARN: Terraform output mcp_invoice_data_url not found; provisioning will rely on config/.env" >&2
fi

(
	cd "$AGENT_PROVISION_DIR"
	uv run python provision_all.py "${AGENT_ARGS[@]}"
)

echo
echo "[3/4] Terraform apply (bootstrap_with_hello_world=false)"
(
	cd "$TERRAFORM_DIR"
	terraform apply -auto-approve -var="bootstrap_with_hello_world=false"
)

echo
echo "[4/4] Deploy Static Web App frontend"

if [[ -z "$SWA_NAME" || "$SWA_NAME" == "null" ]]; then
	echo "SKIP: Static Web App not enabled (static_web_app_name is empty)"
	echo "✓ Done"
	exit 0
fi

if [[ ! -d "$FRONTEND_DIR" ]]; then
	echo "WARN: Frontend directory not found: $FRONTEND_DIR" >&2
	echo "✓ Done"
	exit 0
fi

if ! command -v az >/dev/null 2>&1; then
	echo "WARN: Azure CLI (az) not found; skipping SWA deploy" >&2
	echo "✓ Done"
	exit 0
fi

if ! command -v swa >/dev/null 2>&1; then
	echo "WARN: SWA CLI (swa) not found; install with: npm i -g @azure/static-web-apps-cli" >&2
	echo "WARN: Skipping SWA deploy" >&2
	echo "✓ Done"
	exit 0
fi

if [[ -z "$RESOURCE_GROUP_NAME" || "$RESOURCE_GROUP_NAME" == "null" ]]; then
	echo "WARN: Terraform output resource_group_name not found; skipping SWA deploy" >&2
	echo "✓ Done"
	exit 0
fi

echo "Retrieving SWA deployment token for '$SWA_NAME' (resource group: '$RESOURCE_GROUP_NAME')..." >&2
DEPLOY_TOKEN="$(az staticwebapp secrets list -g "$RESOURCE_GROUP_NAME" -n "$SWA_NAME" --query "properties.apiKey" -o tsv 2>/dev/null || true)"

if [[ -z "$DEPLOY_TOKEN" || "$DEPLOY_TOKEN" == "null" ]]; then
	echo "WARN: Failed to retrieve SWA deployment token; skipping SWA deploy" >&2
	echo "✓ Done"
	exit 0
fi

export SWA_CLI_DEPLOYMENT_TOKEN="$DEPLOY_TOKEN"

echo "Deploying frontend from $FRONTEND_DIR to SWA (env: production)..." >&2
swa deploy "$FRONTEND_DIR" --env production

echo
echo "✓ Done"
