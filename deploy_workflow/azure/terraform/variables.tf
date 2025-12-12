variable "subscription_id" {
  description = <<-EOT
    The Azure subscription ID where resources will be deployed.

    Example: "12345678-1234-1234-1234-123456789abc"
  EOT
  type        = string
}

variable "project_name" {
  description = <<-EOT
    Project name used for resource naming. Lowercase alphanumeric and hyphens.

    Example: "invoice-wf"
  EOT
  type        = string
  default     = "invoice-wf"
}

variable "resource_group_name" {
  description = <<-EOT
    Name of the Azure Resource Group to create.

    Example: "rg-invoice-wf"
  EOT
  type        = string
  default     = "rg-invoice-wf"
}

variable "location" {
  description = <<-EOT
    Azure region for resources.

    Default is eastus2 per requirements.
  EOT
  type        = string
  default     = "eastus2"
}

# ==========================================================================
# Container Apps sizing
# ==========================================================================

variable "backend_container_cpu" {
  description = "CPU cores for workflow backend Container App."
  type        = number
  default     = 0.5
}

variable "backend_container_memory" {
  description = "Memory for workflow backend Container App (e.g. 1.0Gi)."
  type        = string
  default     = "1.0Gi"
}

variable "mcp_container_cpu" {
  description = "CPU cores for MCP Invoice Data Container App."
  type        = number
  default     = 0.25
}

variable "mcp_container_memory" {
  description = "Memory for MCP Invoice Data Container App (e.g. 0.5Gi)."
  type        = string
  default     = "0.5Gi"
}

variable "min_replicas" {
  description = "Minimum replicas for Container Apps."
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Maximum replicas for Container Apps."
  type        = number
  default     = 3
}

variable "deploy_container_apps" {
  description = <<-EOT
    Whether to create/update the Container Apps.

    This is useful for a two-phase deployment:
    1) deploy ACR/Foundry/identity first (deploy_container_apps=false)
    2) build and push images to ACR
    3) enable Container Apps (deploy_container_apps=true)
  EOT
  type        = bool
  default     = true
}

variable "bootstrap_with_hello_world" {
  description = <<-EOT
    Use public hello-world placeholder images for Container Apps.

    This avoids failing `terraform apply` before ACR images exist.
    Once you build and push images to ACR, set this to false and re-apply.
  EOT
  type        = bool
  default     = true
}

# ==========================================================================
# Images
# ==========================================================================

variable "workflow_backend_image" {
  description = "Override image for workflow backend. If empty, uses ACR workflow-backend:latest."
  type        = string
  default     = ""
}

variable "mcp_invoice_data_image" {
  description = "Override image for MCP invoice data server. If empty, uses ACR mcp-invoice-data:latest."
  type        = string
  default     = ""
}

# ==========================================================================
# Secrets
# ==========================================================================

variable "mcp_invoice_api_key" {
  description = <<-EOT
    Static token for mcp-invoice-data (FastMCP StaticTokenVerifier).

    Generate: openssl rand -hex 32
  EOT
  type        = string
  sensitive   = true
}

# ==========================================================================
# Foundry model capacities
# ==========================================================================

variable "gpt5_capacity" {
  description = "Capacity (thousands TPM) for gpt-5 GlobalStandard deployment."
  type        = number
  default     = 900
}

variable "gpt4o_mini_capacity" {
  description = "Capacity (thousands TPM) for gpt-4o-mini GlobalStandard deployment."
  type        = number
  default     = 900
}

variable "gpt5_version" {
  description = "Model version string for gpt-5 deployment."
  type        = string
  default     = "2025-08-07"
}

variable "gpt4o_mini_version" {
  description = "Model version string for gpt-4o-mini deployment."
  type        = string
  default     = "2024-07-18"
}

# ==========================================================================
# Azure Static Web App (optional)
# ==========================================================================

variable "enable_static_web_app" {
  description = "Whether to create an Azure Static Web App resource. Repo integration is optional."
  type        = bool
  default     = true
}

variable "swa_name" {
  description = "Static Web App name (if enabled)."
  type        = string
  default     = "swa-invoice-wf"
}

variable "swa_repo_url" {
  description = "GitHub repo URL to connect to Static Web App (if enabled)."
  type        = string
  default     = ""
}

variable "swa_branch" {
  description = "Git branch for Static Web App (if enabled)."
  type        = string
  default     = "main"
}

variable "swa_github_token" {
  description = "GitHub token for Static Web App repo integration (if enabled)."
  type        = string
  default     = ""
  sensitive   = true
}
