# Cofilot AI Platform - Azure Terraform Deployment

This directory contains Terraform configuration for deploying the Cofilot AI Platform infrastructure to Azure.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.5.0
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (for authentication)
- An Azure subscription

## Resources Created

### Core Infrastructure
- **Resource Group**: Container for all resources
- **Log Analytics Workspace**: Centralized logging for all services
- **Application Insights**: Distributed tracing and telemetry

### Azure AI Foundry
- **AI Services Account**: Next-gen AI Foundry hub with hosted agents support
- **AI Foundry Project**: Project for organizing AI resources
- **Model Deployments**: gpt-5 and gpt-5-mini (GlobalStandard)

### Container Infrastructure
- **Azure Container Registry**: Private registry for container images
- **Container Apps Environment**: Managed environment for containers
- **Container App (MCP Scratchpad)**: Shared scratchpad MCP server

### API Management (AI Gateway)
- **API Management (Standard V2)**: Centralized API gateway for AI model access
- **Azure OpenAI API**: Imported API with chat completions, list/get deployments
- **AI Gateway Connection**: Account-level ApiManagement connection with `isDefault=true`
  - Enables the "AI Gateway" tab in Foundry Admin console
  - Allows token rate limiting and quota management per project
  - Automatically inherited by all projects in the Foundry resource

### RBAC & Security
- **AcrPull roles**: For Foundry project and Container Apps identities
- **Cognitive Services roles**: For accessing Azure OpenAI

## Quick Start

1. **Login to Azure**:
   ```bash
   az login
   ```

2. **Copy and configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Review the plan**:
   ```bash
   terraform plan -var-file=demo.tfvars
   ```

5. **Apply the configuration**:
   ```bash
   terraform apply -var-file=demo.tfvars
   ```

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `subscription_id` | Your Azure subscription ID |
| `mcp_auth_token` | Authentication token for MCP server (keep secret!) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_name` | `summit-ai` | Project name for resource naming |
| `resource_group_name` | `rg-summit-ai` | Name of the resource group |
| `location` | `northcentralus` | Azure region (North Central US for hosted agents preview) |
| `gpt5_capacity` | `50` | Tokens per minute (thousands) for gpt-5 |
| `gpt5_mini_capacity` | `100` | Tokens per minute (thousands) for gpt-5-mini |
| `apim_publisher_email` | `api-admin@example.com` | Email for APIM publisher |
| `apim_publisher_name` | `AI Platform` | Organization name for APIM |
| `apim_capacity` | `1` | Scale units for APIM Standard V2 |

## Key Outputs

After deployment, retrieve important values:

```bash
# AI Foundry project endpoint (for agents)
terraform output -raw ai_foundry_project_endpoint

# Azure OpenAI endpoint (for direct model calls)
terraform output -raw azure_openai_endpoint

# Application Insights connection string (for tracing)
terraform output -raw application_insights_connection_string

# ACR login server (for container images)
terraform output -raw acr_login_server

# MCP Scratchpad URL
terraform output -raw container_app_url
```

## Building and Deploying Container Images

After infrastructure is deployed, build and push images:

```bash
cd ../
python build.py --container mcp-scratchpad
python build.py --container agent-location-scout
```

## Observability

All agents should export traces to Application Insights. Set this environment variable:

```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=$(terraform output -raw application_insights_connection_string)
```

View traces and logs:
- **Azure Portal** → Application Insights → Transaction search
- **Azure Portal** → Log Analytics → Logs (Kusto queries)

## Cleanup

To destroy all resources:

```bash
terraform destroy -var-file=demo.tfvars
```

## Troubleshooting

### Container App not starting
- Check the container logs in Azure Portal
- Verify ACR image exists: `az acr repository list --name <acr-name>`
- Check managed identity has AcrPull role

### Model deployment failures
- Verify model availability in North Central US
- Check quota limits in Azure Portal → Cognitive Services → Quotas

### Tracing not appearing
- Verify `APPLICATIONINSIGHTS_CONNECTION_STRING` is set
- Check agent has `azure-monitor-opentelemetry` dependency
- Wait 2-5 minutes for traces to appear in portal
