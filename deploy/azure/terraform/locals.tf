locals {
  # Resource naming prefix
  name_prefix = "mcp-scratchpad"

  # Common tags applied to all resources
  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  # Container images - use ACR if variable is empty, otherwise use provided value
  mcp_scratchpad_image = (
    var.mcp_scratchpad_image != ""
    ? var.mcp_scratchpad_image
    : "${azurerm_container_registry.main.login_server}/mcp-scratchpad:latest"
  )

  agent_location_scout_image = (
    var.agent_location_scout_image != ""
    ? var.agent_location_scout_image
    : "${azurerm_container_registry.main.login_server}/agent-location-scout:latest"
  )

  # ============================================================================
  # AI Foundry Endpoints (computed from Terraform-managed resources)
  # ============================================================================

  # Main AI Services endpoint
  ai_foundry_endpoint = azapi_resource.ai_foundry_account.output.properties.endpoint

  # AI Foundry API endpoint for projects
  ai_foundry_project_endpoint = "https://ai-${var.project_name}-${random_string.suffix.result}.services.ai.azure.com/api/projects/${var.project_name}-project"

  # OpenAI endpoint for chat completions
  azure_openai_endpoint = "https://ai-${var.project_name}-${random_string.suffix.result}.openai.azure.com/"

  # Foundry account principal ID (for RBAC)
  ai_foundry_account_principal_id = azapi_resource.ai_foundry_account.output.identity.principalId

  # Foundry project principal ID (for RBAC)
  ai_foundry_project_principal_id = azapi_resource.ai_foundry_project.output.identity.principalId
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}
