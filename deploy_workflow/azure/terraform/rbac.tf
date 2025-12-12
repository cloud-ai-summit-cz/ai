# ==========================================================================
# RBAC
# ==========================================================================

# Foundry access for managed identity (runtime)
resource "azurerm_role_assignment" "cognitive_services_user_workflow_identity" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.workflow.principal_id
}

# Requirement: "Azure AI user" for managed identity on Foundry project
resource "azurerm_role_assignment" "azure_ai_user_workflow_identity" {
  scope                = azapi_resource.ai_foundry_project.id
  role_definition_name = "Azure AI User"
  principal_id         = azurerm_user_assigned_identity.workflow.principal_id
}

# Helpful for development: allow current user to manage agents
resource "azurerm_role_assignment" "azure_ai_developer_current" {
  scope                = azapi_resource.ai_foundry_project.id
  role_definition_name = "Azure AI Developer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "cognitive_services_user_current" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services User"
  principal_id         = data.azurerm_client_config.current.object_id
}
