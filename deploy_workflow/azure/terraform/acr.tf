resource "azurerm_container_registry" "main" {
  name                = "acr${replace(var.resource_group_name, "-", "")}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = local.common_tags
}

data "azurerm_client_config" "current" {}

resource "azurerm_role_assignment" "acr_push_current_user" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_user_assigned_identity" "workflow" {
  name                = "id-workflow-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags
}

# Requirement: managed identity can build/pull images from ACR
# AcrPush implies pull; grants push+pull.
resource "azurerm_role_assignment" "acr_push_workflow_identity" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.workflow.principal_id
}
