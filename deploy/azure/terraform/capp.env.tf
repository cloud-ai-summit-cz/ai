# Container Apps Environment
resource "azapi_resource" "container_app_environment" {
  type      = "Microsoft.App/managedEnvironments@2024-03-01"
  name      = "cae-${var.project_name}-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  body = {
    properties = {
      appLogsConfiguration = {
        destination = "log-analytics"
        logAnalyticsConfiguration = {
          customerId = azurerm_log_analytics_workspace.main.workspace_id
          sharedKey  = azurerm_log_analytics_workspace.main.primary_shared_key
        }
      }
      zoneRedundant = false
    }
  }
}