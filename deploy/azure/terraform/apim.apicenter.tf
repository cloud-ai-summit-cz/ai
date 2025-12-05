# ============================================================================
# Azure API Center - Centralized API Catalog
# ============================================================================
# Creates an Azure API Center instance for centralized API discovery, governance,
# and management. Integrates with API Management to synchronize APIs automatically.
#
# Features:
# - Centralized API inventory across the organization
# - API discovery and governance capabilities
# - Integration with APIM for automatic API synchronization
# - Managed identity for secure access to APIM

# ============================================================================
# API Center Service
# ============================================================================
# Creates the Azure API Center instance with system-assigned managed identity.
# The managed identity is used to access APIM for API synchronization.

resource "azapi_resource" "api_center" {
  type      = "Microsoft.ApiCenter/services@2024-03-01"
  name      = "apicenter-${var.project_name}-${random_string.suffix.result}"
  location  = "swedencentral"
  parent_id = azurerm_resource_group.main.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {}
  }

  tags = local.common_tags

  response_export_values = [
    "identity.principalId"
  ]
}

# ============================================================================
# RBAC - API Center Managed Identity Access to APIM
# ============================================================================
# Grants API Center's managed identity the API Management Service Reader role
# on the APIM instance. This allows API Center to read and synchronize APIs.

resource "azurerm_role_assignment" "apim_reader_api_center" {
  scope                = azapi_resource.apim.id
  role_definition_name = "API Management Service Reader Role"
  principal_id         = azapi_resource.api_center.output.identity.principalId
}

# ============================================================================
# API Center Workspace (Default)
# ============================================================================
# References the default workspace that is automatically created by API Center.
# The default workspace is created by the system and cannot be created manually.

data "azapi_resource" "api_center_workspace" {
  type      = "Microsoft.ApiCenter/services/workspaces@2024-03-01"
  name      = "default"
  parent_id = azapi_resource.api_center.id
}

# ============================================================================
# API Center Environment (APIM)
# ============================================================================
# Creates an environment representing the APIM gateway for API deployments.

resource "azapi_resource" "api_center_environment" {
  type      = "Microsoft.ApiCenter/services/workspaces/environments@2024-03-01"
  name      = "apim-gateway"
  parent_id = data.azapi_resource.api_center_workspace.id

  body = {
    properties = {
      title       = "API Management Gateway"
      description = "Azure API Management gateway environment"
      kind        = "production"
      server = {
        type = "Azure API Management"
        managementPortalUri = [
          "https://portal.azure.com/#@/resource${azapi_resource.apim.id}"
        ]
      }
    }
  }
}

# ============================================================================
# API Center Integration with APIM (API Source)
# ============================================================================
# Creates an API source integration to synchronize APIs from APIM to API Center.
# This enables automatic discovery and cataloging of APIs managed in APIM.

resource "azapi_resource" "api_center_apim_source" {
  type      = "Microsoft.ApiCenter/services/workspaces/apiSources@2024-06-01-preview"
  name      = "apim-integration"
  parent_id = data.azapi_resource.api_center_workspace.id

  body = {
    properties = {
      azureApiManagementSource = {
        resourceId = azapi_resource.apim.id
      }
      importSpecification  = "always"
      targetEnvironmentId  = "/workspaces/default/environments/${azapi_resource.api_center_environment.name}"
      targetLifecycleStage = "production"
    }
  }

  depends_on = [
    azurerm_role_assignment.apim_reader_api_center
  ]
}

# ============================================================================
# Outputs
# ============================================================================

output "api_center_name" {
  description = "The name of the Azure API Center instance"
  value       = azapi_resource.api_center.name
}

output "api_center_id" {
  description = "The resource ID of the Azure API Center instance"
  value       = azapi_resource.api_center.id
}
