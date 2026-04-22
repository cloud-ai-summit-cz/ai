# Workflow Azure Deployment

This directory contains infrastructure-as-code (Terraform) and build tooling for deploying the **workflow infrastructure** to Azure.

## What gets deployed

- Default region: **eastus2**
- **Azure Container Registry (ACR)** for container images
- **Azure Container Apps**:
  - Workflow backend (FastAPI) from [src/workflows/backend/Dockerfile](../../src/workflows/backend/Dockerfile)
  - MCP Invoice Data server from [src/mcp-invoice-data/Dockerfile](../../src/mcp-invoice-data/Dockerfile)
- **User Assigned Managed Identity (UAMI)** attached to both Container Apps
- **Azure AI Foundry** account + project
- Model deployments (Global Standard): **gpt-5** and **gpt-4o-mini**
- RBAC:
  - UAMI can pull (and optionally push) images from ACR
  - UAMI granted Foundry access ("Azure AI User" + "Cognitive Services User")

> Note: This Terraform creates an Azure Static Web App by default, but **without** repo integration unless you provide `swa_repo_url` and `swa_github_token`. You can deploy the frontend manually afterward.

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Terraform installed
- Python 3.11+ with `uv`
- Azure permissions: Contributor + ability to create role assignments

## Quick Start

### 1) Deploy infrastructure

```bash
cd deploy_workflow/azure/terraform

terraform init
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars


# By default, Container Apps use a public hello-world image so the first apply
# succeeds even before you've built/pushed your real images to ACR.
# After you build images, set `bootstrap_with_hello_world = false` and re-apply.

terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

### 2) Build container images (ACR Tasks)

After Terraform creates the ACR:

```bash
cd deploy_workflow/azure
uv sync
uv run python build.py           # build all workflow images

# or build one:
uv run python build.py --container workflow-backend
uv run python build.py --container mcp-invoice-data

### 2b) Switch off hello-world bootstrap

Set `bootstrap_with_hello_world = false` in `terraform.tfvars` and re-run:

```bash
cd deploy_workflow/azure/terraform
terraform apply -var-file=terraform.tfvars
```

### 3) Check outputs

```bash
cd deploy_workflow/azure/terraform
terraform output
```

## Frontend (Azure Static Web Apps)

Terraform creates the Static Web App resource by default.

- Manual deployment: leave `swa_repo_url` and `swa_github_token` empty.
- GitHub integration (optional): set `swa_repo_url`, `swa_branch`, and `swa_github_token`.
