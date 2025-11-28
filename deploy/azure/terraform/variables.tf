variable "subscription_id" {
  description = <<-EOT
    The Azure subscription ID where resources will be deployed.
    
    This is required for azurerm provider configuration.
    Can be set via environment variable TF_VAR_subscription_id or passed directly.
    
    Example: "12345678-1234-1234-1234-123456789abc"
  EOT
  type        = string
}

variable "resource_group_name" {
  description = <<-EOT
    The name of the Azure Resource Group to create.
    
    This resource group will contain all resources for the MCP Scratchpad service.
    Must be unique within the subscription.
    
    Example: "rg-mcp-scratchpad-dev"
  EOT
  type        = string
  default     = "rg-summit-ai"
}

variable "location" {
  description = <<-EOT
    The Azure region where resources will be deployed.
    
    Choose a region that supports Azure Container Apps.
    Common options: eastus, westus2, westeurope, northeurope
    
    Example: "sweedentcentral"
  EOT
  type        = string
  default     = "sweedentcentral"
}

variable "container_image" {
  description = <<-EOT
    The container image to deploy for the MCP Scratchpad server.
    
    Should include the full registry path and tag.
    The GitHub Actions workflow pushes to ghcr.io with tag 'latest'.
    
    Example: "ghcr.io/your-org/mcp-scratchpad:latest"
  EOT
  type        = string
  default     = "ghcr.io/tkubica12/mcp-scratchpad:latest"
}

variable "mcp_auth_token" {
  description = <<-EOT
    The authentication token for the MCP Scratchpad server.
    
    This token is required for clients to authenticate with the MCP server.
    Should be a secure random string. Keep this secret!
    
    Example: "your-secure-random-token-here"
  EOT
  type        = string
  sensitive   = true
}

variable "container_cpu" {
  description = <<-EOT
    CPU cores allocated to the container.
    
    Azure Container Apps supports: 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
    For development/demo, 0.25 is sufficient.
    
    Example: 0.25
  EOT
  type        = number
  default     = 0.25
}

variable "container_memory" {
  description = <<-EOT
    Memory allocated to the container in Gi.
    
    Must be compatible with CPU allocation per Azure Container Apps requirements.
    For 0.25 CPU, use 0.5Gi. For 0.5 CPU, use 1.0Gi.
    
    Example: "0.5Gi"
  EOT
  type        = string
  default     = "0.5Gi"
}

variable "min_replicas" {
  description = <<-EOT
    Minimum number of container replicas.
    
    Set to 0 for scale-to-zero (cost savings in dev).
    Set to 1+ for production to avoid cold starts.
    
    Example: 0
  EOT
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = <<-EOT
    Maximum number of container replicas for auto-scaling.
    
    The container app will scale between min_replicas and max_replicas
    based on HTTP traffic.
    
    Example: 3
  EOT
  type        = number
  default     = 3
}
