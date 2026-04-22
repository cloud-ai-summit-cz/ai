variable "subscription_id" {
  description = <<-EOT
    The Azure subscription ID where resources will be deployed.
    
    This is required for azurerm provider configuration.
    Can be set via environment variable TF_VAR_subscription_id or passed directly.
    
    Example: "12345678-1234-1234-1234-123456789abc"
  EOT
  type        = string
}

variable "project_name" {
  description = <<-EOT
    The name of the project used for resource naming.
    
    This will be used as a prefix/suffix for Azure resources
    including the AI Foundry account, project, and other services.
    Must be 3-24 characters, lowercase alphanumeric.
    
    Example: "summit-ai"
  EOT
  type        = string
  default     = "summit-ai"
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
    
    Example: "northcentralus"
  EOT
  type        = string
  default     = "northcentralus"
}

variable "mcp_scratchpad_image" {
  description = <<-EOT
    The container image to deploy for the MCP Scratchpad server.
    
    Should include the full registry path and tag.
    Use ACR images built via deploy/azure/build.py.
    
    Example: "myacr.azurecr.io/mcp-scratchpad:latest"
  EOT
  type        = string
  default     = "" # Will be computed from ACR if empty
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
  default     = 1
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

# ============================================================================
# Agent Location Scout Variables
# ============================================================================

variable "agent_location_scout_image" {
  description = <<-EOT
    The container image for the Agent Location Scout.
    
    This is a LangGraph-based agent hosted via azure-ai-agentserver-langgraph.
    Use ACR images built via deploy/azure/build.py.
    
    Example: "myacr.azurecr.io/agent-location-scout:latest"
  EOT
  type        = string
  default     = "" # Will be computed from ACR if empty
}

variable "azure_ai_model_deployment_name" {
  description = <<-EOT
    The Azure OpenAI model deployment name.
    
    The name of the deployed model in Azure OpenAI/Foundry.
    This should match one of the deployments created by Terraform.
    
    Example: "gpt-5"
  EOT
  type        = string
  default     = "gpt-5"
}

# ============================================================================
# AI Foundry Model Capacity Variables
# ============================================================================

variable "gpt5_capacity" {
  description = <<-EOT
    Capacity (in thousands of tokens per minute) for the gpt-5 model deployment.
    
    GlobalStandard deployments bill based on usage, but capacity sets the rate limit.
    Typical values: 10-100 for development, 100-1000 for production.
    
    Example: 50
  EOT
  type        = number
  default     = 900
}

variable "gpt5_mini_capacity" {
  description = <<-EOT
    Capacity (in thousands of tokens per minute) for the gpt-5-mini model deployment.
    
    GlobalStandard deployments bill based on usage, but capacity sets the rate limit.
    Typical values: 10-100 for development, 100-1000 for production.
    
    Example: 100
  EOT
  type        = number
  default     = 900
}

variable "agent_container_cpu" {
  description = <<-EOT
    CPU cores allocated to agent containers.
    
    Azure Container Apps supports: 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
    Agents typically need more resources than MCP servers.
    
    Example: 0.5
  EOT
  type        = number
  default     = 0.5
}

variable "agent_container_memory" {
  description = <<-EOT
    Memory allocated to agent containers.
    
    Must be compatible with CPU allocation per Azure Container Apps requirements.
    For 0.5 CPU, use 1.0Gi.
    
    Example: "1.0Gi"
  EOT
  type        = string
  default     = "1.0Gi"
}

variable "agent_min_replicas" {
  description = <<-EOT
    Minimum number of agent container replicas.
    
    Set to 0 for scale-to-zero (cost savings in dev).
    Set to 1+ for production to avoid cold starts.
    
    Example: 0
  EOT
  type        = number
  default     = 0
}

variable "agent_max_replicas" {
  description = <<-EOT
    Maximum number of agent container replicas.
    
    The container app will scale between min and max based on HTTP traffic.
    
    Example: 5
  EOT
  type        = number
  default     = 5
}

# ============================================================================
# Azure API Management Variables
# ============================================================================

variable "apim_publisher_email" {
  description = <<-EOT
    The email address of the API Management publisher.
    
    This email is used for notifications and administrative purposes.
    Must be a valid email address.
    
    Example: "api-admin@example.com"
  EOT
  type        = string
  default     = "api-admin@example.com"
}

variable "apim_publisher_name" {
  description = <<-EOT
    The name of the API Management publisher/organization.
    
    This name appears in the developer portal and API documentation.
    
    Example: "Contoso AI Platform"
  EOT
  type        = string
  default     = "AI Platform"
}

variable "apim_capacity" {
  description = <<-EOT
    The capacity (scale units) for the API Management instance.
    
    For StandardV2 tier, each unit provides additional throughput.
    Typical values: 1 for development, 2+ for production.
    
    Example: 1
  EOT
  type        = number
  default     = 1
}

# ============================================================================
# A2A Agent Authentication
# ============================================================================

variable "a2a_api_key" {
  description = <<-EOT
    The API key for authenticating with A2A agents.
    
    This key is required for clients to authenticate with A2A protocol agents.
    Should be a secure random string. Keep this secret!
    Generate with: openssl rand -hex 32
    
    Example: "your-secure-random-a2a-key-here"
  EOT
  type        = string
  sensitive   = true
}

# ============================================================================
# Azure Container Registry Variables
# ============================================================================
