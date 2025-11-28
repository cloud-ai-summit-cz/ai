# MCP Scratchpad - Azure Terraform Deployment

This directory contains Terraform configuration for deploying the MCP Scratchpad server to Azure Container Apps.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.5.0
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (for authentication)
- An Azure subscription
- The MCP Scratchpad container image pushed to GitHub Container Registry

## Resources Created

- **Resource Group**: Container for all resources
- **Log Analytics Workspace**: For monitoring and logging
- **Container Apps Environment**: Managed environment for container apps
- **Container App**: The MCP Scratchpad server

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
   terraform plan
   ```

5. **Apply the configuration**:
   ```bash
   terraform apply
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
| `resource_group_name` | `rg-mcp-scratchpad` | Name of the resource group |
| `location` | `westeurope` | Azure region |
| `environment` | `dev` | Environment name (dev/staging/prod) |
| `container_image` | `ghcr.io/tkubica12/mcp-scratchpad:latest` | Container image to deploy |
| `container_cpu` | `0.25` | CPU cores for container |
| `container_memory` | `0.5Gi` | Memory for container |
| `min_replicas` | `0` | Minimum replicas (0 = scale to zero) |
| `max_replicas` | `3` | Maximum replicas for auto-scaling |

## Outputs

After deployment, Terraform will output:

- `container_app_url`: The URL to access the MCP Scratchpad server
- `container_app_fqdn`: The fully qualified domain name
- `resource_group_name`: The resource group name
- `log_analytics_workspace_id`: For monitoring queries

## Connecting to the MCP Server

Once deployed, connect to the MCP Scratchpad server using the URL from outputs:

```python
from mcp import ClientSession

async with ClientSession(
    url="https://<container_app_fqdn>/mcp",
    headers={"Authorization": "Bearer <your-mcp-auth-token>"}
) as session:
    # Use MCP tools
    result = await session.call_tool("list_sections", {"session_id": "my-session"})
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Troubleshooting

### Container App not starting
- Check the container logs in Azure Portal or via CLI
- Verify the container image exists and is accessible
- Check the `MCP_AUTH_TOKEN` secret is correctly set

### Health check failures
- The server exposes `/health` endpoint on port 8080
- Ensure the container has enough resources (CPU/memory)

### Authentication errors
- Verify the `MCP_AUTH_TOKEN` matches what clients are using
- Check the authorization header format: `Bearer <token>`
