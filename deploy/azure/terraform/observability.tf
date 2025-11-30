# ============================================================================
# Observability - Application Insights
# ============================================================================
# Application Insights for tracing and telemetry from agents and Foundry.
# Connected to Log Analytics workspace for unified observability.

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "appi-${var.project_name}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"

  tags = local.common_tags
}

# ============================================================================
# Foundry Diagnostic Settings
# ============================================================================
# Connect AI Foundry to Application Insights for tracing

resource "azapi_resource" "foundry_diagnostic_settings" {
  type      = "Microsoft.Insights/diagnosticSettings@2021-05-01-preview"
  name      = "diag-foundry-to-appinsights"
  parent_id = azapi_resource.ai_foundry_account.id

  body = {
    properties = {
      workspaceId = azurerm_log_analytics_workspace.main.id
      logs = [
        {
          categoryGroup = "allLogs"
          enabled       = true
        }
      ]
      metrics = [
        {
          category = "AllMetrics"
          enabled  = true
        }
      ]
    }
  }
}
