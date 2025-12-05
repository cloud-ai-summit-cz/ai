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

  # MCP Business Registry image
  mcp_business_registry_image = "${azurerm_container_registry.main.login_server}/mcp-business-registry:latest"

  # MCP Government Data image
  mcp_government_data_image = "${azurerm_container_registry.main.login_server}/mcp-government-data:latest"

  # MCP Demographics image
  mcp_demographics_image = "${azurerm_container_registry.main.login_server}/mcp-demographics:latest"

  # MCP Real Estate image
  mcp_real_estate_image = "${azurerm_container_registry.main.login_server}/mcp-real-estate:latest"

  # MCP Calculator image
  mcp_calculator_image = "${azurerm_container_registry.main.login_server}/mcp-calculator:latest"

  # Agent Market Analyst A2A image
  agent_market_analyst_a2a_image = "${azurerm_container_registry.main.login_server}/agent-market-analyst-a2a:latest"

  # Agent Competitor Analyst A2A image
  agent_competitor_analyst_a2a_image = "${azurerm_container_registry.main.login_server}/agent-competitor-analyst-a2a:latest"

  # Agent Finance Analyst A2A image
  agent_finance_analyst_a2a_image = "${azurerm_container_registry.main.login_server}/agent-finance-analyst-a2a:latest"

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
