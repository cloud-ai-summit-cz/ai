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
  value       = azapi_resource.container_app.name
}

output "container_app_fqdn" {
  description = "The fully qualified domain name of the Container App"
  value       = jsondecode(azapi_resource.container_app.output).properties.configuration.ingress.fqdn
}

output "container_app_url" {
  description = "The URL to access the MCP Scratchpad server"
  value       = "https://${jsondecode(azapi_resource.container_app.output).properties.configuration.ingress.fqdn}"
}

output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics Workspace"
  value       = azurerm_log_analytics_workspace.main.id
}
