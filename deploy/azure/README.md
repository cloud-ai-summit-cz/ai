# Azure Deployment

This directory contains infrastructure-as-code (Terraform) and build tooling for deploying the Cofilot AI Platform to Azure.

## Directory Structure

```
deploy/azure/
├── terraform/          # Terraform configuration for Azure resources
├── build.py            # Build script for ACR Tasks
├── build-config.yaml   # Container build configuration
├── pyproject.toml      # Python dependencies for build tooling
└── README.md           # This file
```

## Prerequisites

- Azure CLI installed and logged in (`az login`)
- Terraform installed
- Python 3.11+ with uv package manager
- Appropriate Azure permissions (Contributor + Role Assignment rights)

## Quick Start

### 1. Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Create a .tfvars file (use demo.tfvars as template)
cp demo.tfvars my.tfvars
# Edit my.tfvars with your values

# Plan and apply
terraform plan -var-file=my.tfvars
terraform apply -var-file=my.tfvars
```

### 2. Build Container Images

After deploying infrastructure (which creates the ACR), build all 13 containers:

```bash
cd deploy/azure
uv sync
uv run python build.py        # Build all containers (uses ACR Tasks - no local Docker needed)
```

**Build options:**
```bash
uv run python build.py --container mcp-scratchpad   # Build specific container
uv run python build.py --list                       # List available containers
```

**Containers built (see `build-config.yaml`):**
- **MCP Servers**: mcp-scratchpad, mcp-business-registry, mcp-government-data, mcp-demographics, mcp-real-estate, mcp-calculator
- **Agents (A2A)**: agent-market-analyst-a2a, agent-competitor-analyst-a2a, agent-finance-analyst-a2a, agent-location-scout-a2a, agent-synthesizer-a2a
- **Services**: agent-research-orchestrator, web-research

## Container Registry

Azure AI Foundry hosted agents **require Azure Container Registry (ACR)**. GitHub Container Registry (GHCR) is not supported for hosted agents.

The Terraform configuration creates:
- ACR with Basic SKU
- AcrPush role for the deploying user/service principal
- AcrPull role for the Azure AI Foundry project (if `foundry_project_principal_id` is set)

### Getting Foundry Project Principal ID

To get the principal ID for your Azure AI Foundry project:

```bash
# Replace placeholders with your values
az rest --method GET \
  --url "https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}?api-version=2025-06-01" \
  --query identity.principalId -o tsv
```

Then add it to your .tfvars:

```terraform
foundry_project_principal_id = "your-principal-id-here"
```

## Build Configuration

The `build-config.yaml` file defines which containers to build:

```yaml
containers:
  - name: mcp-scratchpad
    path: ../../src/mcp-scratchpad
    image: mcp-scratchpad
    tag: latest
    
  - name: agent-location-scout
    path: ../../src/agent-location-scout
    image: agent-location-scout
    tag: latest
```

### Adding a New Container

1. Add the container definition to `build-config.yaml`
2. Ensure the source directory has a `Dockerfile`
3. Run `uv run python build.py --container your-container-name`

## Terraform Resources

The Terraform configuration creates:

| Resource | Description |
|----------|-------------|
| Resource Group | Container for all resources |
| Log Analytics Workspace | Logging for Container Apps |
| Container Apps Environment | Managed Kubernetes for containers |
| Azure Container Registry | Image storage (required for Foundry agents) |
| Container Apps | MCP servers (6), Agents (5), Orchestrator, Web UI |
| Azure API Management | API gateway for all services |
| Azure AI Foundry | Hub + Project for AI model access |
| Role Assignments | ACR access for users and managed identities |

## Outputs

Key Terraform outputs:

| Output | Description |
|--------|-------------|
| `acr_name` | ACR name (used by build.py) |
| `acr_login_server` | ACR login server URL |
| `container_app_url` | URL for MCP Scratchpad |

## Troubleshooting

### ACR Build Fails

1. Ensure you're logged into Azure CLI: `az login`
2. Verify ACR exists: `az acr list --query "[].name" -o tsv`
3. Check you have AcrPush permission

### Terraform State Issues

State is stored locally by default. For team usage, configure remote state:

```terraform
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstate12345"
    container_name       = "tfstate"
    key                  = "cofilot.tfstate"
  }
}
```

### Hosted Agent Won't Start

1. Verify ACR image exists: `az acr repository list --name <acr_name>`
2. Check Foundry project has AcrPull: Check role assignments in Azure Portal
3. Use `provision.py status` in the agent directory for detailed status
