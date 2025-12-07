output "resource_group_name" {
  description = "The name of the created resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "The ID of the created resource group"
  value       = azurerm_resource_group.main.id
}

output "container_app_environment_name" {
  description = "The name of the Container Apps Environment"
  value       = azapi_resource.container_app_environment.name
}

output "container_app_name" {
  description = "The name of the Container App"
  value       = azapi_resource.capp_mcp_scratchpad.name
}

output "container_app_fqdn" {
  description = "The fully qualified domain name of the Container App"
  value       = azapi_resource.capp_mcp_scratchpad.output.properties.configuration.ingress.fqdn
}

output "container_app_url" {
  description = "The URL to access the MCP Scratchpad server"
  value       = "https://${azapi_resource.capp_mcp_scratchpad.output.properties.configuration.ingress.fqdn}"
}

output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_guid" {
  description = "The GUID of the Log Analytics Workspace (for Azure Monitor Query API)"
  value       = azurerm_log_analytics_workspace.main.workspace_id
}

# ============================================================================
# Azure Container Registry Outputs
# ============================================================================

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry"
  value       = azurerm_container_registry.main.login_server
}

output "acr_id" {
  description = "The ID of the Azure Container Registry"
  value       = azurerm_container_registry.main.id
}

# ============================================================================
# Container Image Outputs
# ============================================================================

output "mcp_scratchpad_image" {
  description = "The container image used for MCP Scratchpad"
  value       = local.mcp_scratchpad_image
}

output "agent_location_scout_image" {
  description = "The container image used for Agent Location Scout"
  value       = local.agent_location_scout_image
}

# ============================================================================
# Azure AI Foundry Outputs
# ============================================================================

output "ai_foundry_account_name" {
  description = "The name of the Azure AI Foundry account"
  value       = azapi_resource.ai_foundry_account.name
}

output "ai_foundry_account_id" {
  description = "The resource ID of the Azure AI Foundry account"
  value       = azapi_resource.ai_foundry_account.id
}

output "ai_foundry_endpoint" {
  description = "The main endpoint for Azure AI Foundry account"
  value       = local.ai_foundry_endpoint
}

output "ai_foundry_project_name" {
  description = "The name of the Azure AI Foundry project"
  value       = azapi_resource.ai_foundry_project.name
}

output "ai_foundry_project_endpoint" {
  description = "The API endpoint for the Azure AI Foundry project"
  value       = local.ai_foundry_project_endpoint
}

output "azure_openai_endpoint" {
  description = "The Azure OpenAI endpoint for chat completions"
  value       = local.azure_openai_endpoint
}

output "ai_foundry_project_principal_id" {
  description = "The principal ID of the Foundry project managed identity"
  value       = local.ai_foundry_project_principal_id
}

# ============================================================================
# Model Deployment Outputs
# ============================================================================

output "model_gpt5_name" {
  description = "The deployment name for the gpt-5 model"
  value       = azapi_resource.model_gpt5.name
}

output "model_gpt5_mini_name" {
  description = "The deployment name for the gpt-5-mini model"
  value       = azapi_resource.model_gpt5_mini.name
}

# ============================================================================
# Application Insights Outputs
# ============================================================================

output "application_insights_name" {
  description = "The name of the Application Insights instance"
  value       = azurerm_application_insights.main.name
}

output "application_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "The connection string for Application Insights (use this for newer SDKs)"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

# ============================================================================
# MCP Server Container App Outputs
# ============================================================================

output "mcp_scratchpad_url" {
  description = "The URL for the MCP Scratchpad server"
  value       = "https://${azapi_resource.capp_mcp_scratchpad.output.properties.configuration.ingress.fqdn}/mcp"
}

output "mcp_business_registry_url" {
  description = "The URL for the MCP Business Registry server"
  value       = "https://${azapi_resource.capp_mcp_business_registry.output.properties.configuration.ingress.fqdn}/mcp"
}

output "mcp_government_data_url" {
  description = "The URL for the MCP Government Data server"
  value       = "https://${azapi_resource.capp_mcp_government_data.output.properties.configuration.ingress.fqdn}/mcp"
}

output "mcp_demographics_url" {
  description = "The URL for the MCP Demographics server"
  value       = "https://${azapi_resource.capp_mcp_demographics.output.properties.configuration.ingress.fqdn}/mcp"
}

output "mcp_real_estate_url" {
  description = "The URL for the MCP Real Estate server"
  value       = "https://${azapi_resource.capp_mcp_real_estate.output.properties.configuration.ingress.fqdn}/mcp"
}

output "mcp_calculator_url" {
  description = "The URL for the MCP Calculator server"
  value       = "https://${azapi_resource.capp_mcp_calculator.output.properties.configuration.ingress.fqdn}/mcp"
}

# ============================================================================
# MCP Project Connection Names
# ============================================================================
# These are the connection names to use with project_connection_id in MCPTool

output "mcp_connection_scratchpad" {
  description = "The Foundry project connection name for MCP Scratchpad"
  value       = azapi_resource.mcp_connection_scratchpad.name
}

output "mcp_connection_business_registry" {
  description = "The Foundry project connection name for MCP Business Registry"
  value       = azapi_resource.mcp_connection_business_registry.name
}

output "mcp_connection_government_data" {
  description = "The Foundry project connection name for MCP Government Data"
  value       = azapi_resource.mcp_connection_government_data.name
}

output "mcp_connection_demographics" {
  description = "The Foundry project connection name for MCP Demographics"
  value       = azapi_resource.mcp_connection_demographics.name
}

output "mcp_connection_real_estate" {
  description = "The Foundry project connection name for MCP Real Estate"
  value       = azapi_resource.mcp_connection_real_estate.name
}

output "mcp_connection_calculator" {
  description = "The Foundry project connection name for MCP Calculator"
  value       = azapi_resource.mcp_connection_calculator.name
}

# ============================================================================
# Azure API Management Outputs
# ============================================================================

output "apim_name" {
  description = "The name of the API Management instance"
  value       = azapi_resource.apim.name
}

output "apim_gateway_url" {
  description = "The gateway URL of the API Management instance"
  value       = azapi_resource.apim.output.properties.gatewayUrl
}

output "apim_management_url" {
  description = "The management API URL of the API Management instance"
  value       = azapi_resource.apim.output.properties.managementApiUrl
}

output "apim_openai_api_url" {
  description = "The URL for accessing Azure OpenAI through APIM"
  value       = "${azapi_resource.apim.output.properties.gatewayUrl}/openai"
}

output "apim_foundry_connection_name" {
  description = "The name of the APIM connection in Foundry"
  value       = azapi_resource.foundry_apim_connection.name
}

output "apim_principal_id" {
  description = "The principal ID of the APIM managed identity"
  value       = azapi_resource.apim.output.identity.principalId
}
