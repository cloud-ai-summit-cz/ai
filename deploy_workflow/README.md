# Full workflow deployment (Terraform + Agents + SWA)

This folder contains a one-command deployment for the invoice workflow demo.

## What `deploy_all.sh` does

Runs these steps in order:

1. `terraform apply` with `bootstrap_with_hello_world=true`
2. Provisions all Foundry agents via `agent_provisioning/provision_all.py`
3. `terraform apply` with `bootstrap_with_hello_world=false`
4. Deploys the static frontend to Azure Static Web Apps (SWA)

Terraform outputs are used to wire things up automatically:
- `ai_foundry_project_endpoint` → passed to agent provisioners
- `mcp_invoice_data_url` → passed to agent provisioners (script appends `/mcp` if needed)
- `static_web_app_name` + `resource_group_name` → used for SWA deployment

## Prerequisites

- Azure login: `az login`
- Tools installed:
  - `terraform`
  - `uv`
  - Azure CLI `az`
  - SWA CLI `swa` (install: `npm i -g @azure/static-web-apps-cli`)

## Configure Terraform

From `deploy_workflow/azure/terraform/`:

- Copy `terraform.tfvars.example` → `terraform.tfvars`
- Fill in at least:
  - `subscription_id`
  - `mcp_invoice_api_key`
- Ensure `enable_static_web_app = true` if you want the frontend deployed

## Run

From repo root:

- `bash deploy_workflow/deploy_all.sh`

If SWA is disabled or `az`/`swa` aren’t available, the SWA step is skipped safely.


## Manual Steps

- Add MCP server to at least one agent through Foundry portal (current limitation)
- Create workflow based on YAML in `src/workflows/invoice-processing-seq/workflow.yaml`
