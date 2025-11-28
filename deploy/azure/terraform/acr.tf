# Azure Container Registry
# Used for hosting container images for agents and MCP servers.
# Azure AI Foundry hosted agents require ACR (GHCR is not supported).

resource "azurerm_container_registry" "main" {
  name                = "acr${replace(var.resource_group_name, "-", "")}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false

  tags = local.common_tags
}

# Get current client configuration for role assignment
data "azurerm_client_config" "current" {}

# AcrPush role for the current user/service principal running Terraform
# This allows the build script to push images to ACR
resource "azurerm_role_assignment" "acr_push_current_user" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = data.azurerm_client_config.current.object_id
}

# AcrPull role for the Azure AI Foundry project
# This allows hosted agents to pull images from ACR
resource "azurerm_role_assignment" "acr_pull_foundry_project" {
  count                = var.foundry_project_principal_id != "" ? 1 : 0
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = var.foundry_project_principal_id
}

# AcrPull role for Container Apps managed identity (if needed in future)
# resource "azurerm_role_assignment" "acr_pull_container_apps" {
#   scope                = azurerm_container_registry.main.id
#   role_definition_name = "AcrPull"
#   principal_id         = azapi_resource.container_app_environment.identity[0].principal_id
# }

# User-Assigned Managed Identity for Container Apps to pull from ACR
# Created separately so role assignment can complete before Container App uses it
resource "azurerm_user_assigned_identity" "container_apps" {
  name                = "id-container-apps-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags
}

# AcrPull role for Container Apps user-assigned identity
resource "azurerm_role_assignment" "acr_pull_container_apps" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_apps.principal_id
}
