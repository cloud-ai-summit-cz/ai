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
