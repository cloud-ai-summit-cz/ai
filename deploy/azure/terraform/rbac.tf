# ============================================================================
# RBAC - Role Assignments
# ============================================================================
# Role assignments for Azure AI Foundry, Container Apps, and ACR integration.

# ============================================================================
# ACR Access for Foundry Project
# ============================================================================

# AcrPull role for the Azure AI Foundry project managed identity
# This allows hosted agents to pull container images from ACR
resource "azurerm_role_assignment" "acr_pull_foundry_project" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = local.ai_foundry_project_principal_id
}

# ============================================================================
# Cognitive Services Access for Container Apps
# ============================================================================

# Cognitive Services User role for Container Apps managed identity
# This allows agents deployed in Container Apps to call Azure OpenAI
resource "azurerm_role_assignment" "cognitive_services_user_container_apps" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# ============================================================================
# Cognitive Services Access for Current User (development)
# ============================================================================

# Cognitive Services User role for the current user running Terraform
# This allows local development and testing with Azure OpenAI
resource "azurerm_role_assignment" "cognitive_services_user_current" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Cognitive Services Contributor role for the current user
# This allows managing deployments and configurations
resource "azurerm_role_assignment" "cognitive_services_contributor_current" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ============================================================================
# Azure AI Foundry Project Access for Current User (development)
# ============================================================================

# Azure AI User role for the current user on the Foundry project
# This allows creating/managing agents via the Azure AI Foundry SDK
# Required for: Microsoft.CognitiveServices/accounts/AIServices/agents/* dataActions
# See: https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/rbac-azure-ai-foundry
resource "azurerm_role_assignment" "ai_user_current" {
  scope                = azapi_resource.ai_foundry_project.id
  role_definition_name = "Azure AI User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ============================================================================
# Application Insights Access for Tracing
# ============================================================================
# RBAC required for Foundry tracing integration per:
# https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/trace-application

# Log Analytics Reader role for current user on Application Insights
# Required to view traces in Foundry portal's Tracing UI
resource "azurerm_role_assignment" "log_analytics_reader_current" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Log Analytics Reader role for Foundry account managed identity
# Required for Foundry to read traces from Application Insights
resource "azurerm_role_assignment" "log_analytics_reader_foundry_account" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = local.ai_foundry_account_principal_id
}

# Log Analytics Reader role for Foundry project managed identity
# Required for project-level trace access
resource "azurerm_role_assignment" "log_analytics_reader_foundry_project" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = local.ai_foundry_project_principal_id
}

# Monitoring Metrics Publisher role for Container Apps managed identity
# Required for Container Apps to publish telemetry to Application Insights
resource "azurerm_role_assignment" "monitoring_metrics_publisher_container_apps" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}

# Monitoring Metrics Publisher role for Foundry project managed identity
# Required for Foundry-hosted agents to publish telemetry to Application Insights
resource "azurerm_role_assignment" "monitoring_metrics_publisher_foundry_project" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = local.ai_foundry_project_principal_id
}

# Monitoring Metrics Publisher role for Foundry account managed identity
# Required for the Foundry account to publish telemetry to Application Insights
resource "azurerm_role_assignment" "monitoring_metrics_publisher_foundry_account" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Monitoring Metrics Publisher"
  principal_id         = local.ai_foundry_account_principal_id
}
