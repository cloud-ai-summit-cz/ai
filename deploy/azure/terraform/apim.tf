# ============================================================================
# Azure API Management (Standard v2) - Base Configuration
# ============================================================================
# API Management instance for AI Gateway integration with Azure AI Foundry.
# Uses Standard v2 tier as required for Foundry Agents APIM connection.
# Provides centralized API management, rate limiting, and security for AI models.
#
# File Structure:
# - apim.tf          : Base APIM service, Foundry connection, and RBAC (this file)
# - apim.genai.tf    : GenAI gateway resources (OpenAI API, subscriptions, policies)
# - apim.<agent>.tf  : A2A agent registrations (one file per agent)

# ============================================================================
# API Management Service
# ============================================================================

resource "azapi_resource" "apim" {
  type      = "Microsoft.ApiManagement/service@2024-05-01"
  name      = "apim-${var.project_name}-${random_string.suffix.result}"
  location  = var.location
  parent_id = azurerm_resource_group.main.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    sku = {
      name     = "StandardV2"
      capacity = var.apim_capacity
    }
    properties = {
      publisherEmail      = var.apim_publisher_email
      publisherName       = var.apim_publisher_name
      publicNetworkAccess = "Enabled"
      virtualNetworkType  = "None"
    }
  }

  tags = local.common_tags

  response_export_values = [
    "properties.gatewayUrl",
    "properties.managementApiUrl",
    "properties.developerPortalUrl",
    "identity.principalId"
  ]

  # APIM Standard v2 can take 30-45 minutes to provision
  timeouts {
    create = "60m"
    update = "60m"
    delete = "30m"
  }
}

# ============================================================================
# APIM Connection to Azure AI Foundry (AI Gateway)
# ============================================================================
# Creates an ApiManagement category connection at the ACCOUNT level with isDefault=true.
# This enables the AI Gateway feature in Foundry Admin console for token rate limiting
# and quota management. The connection is automatically inherited by all projects.
#
# Key properties discovered from portal-created AI Gateway:
# - Must be at ACCOUNT level (accounts/connections), not project level
# - isDefault = true (marks this as the default AI Gateway)
# - isSharedToAll = false (inherited differently than project connections)

resource "azapi_resource" "foundry_apim_connection" {
  type                      = "Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview"
  name                      = "apim-gateway"
  parent_id                 = azapi_resource.ai_foundry_account.id
  schema_validation_enabled = false

  body = {
    properties = {
      category      = "ApiManagement"
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/openai"
      authType      = "ApiKey"
      isDefault     = true
      isSharedToAll = false
      credentials = {
        key = random_password.apim_subscription_key.result
      }
      metadata = {
        deploymentInPath    = "true"
        inferenceAPIVersion = "2024-02-01"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.apim_api_policy
  ]
}

# ============================================================================
# RBAC for APIM Managed Identity
# ============================================================================
# Grants APIM's managed identity access to Azure OpenAI for backend calls.

resource "azurerm_role_assignment" "cognitive_services_user_apim" {
  scope                = azapi_resource.ai_foundry_account.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azapi_resource.apim.output.identity.principalId
}

# Reader role on Resource Group for APIM to list deployments via ARM API
resource "azurerm_role_assignment" "reader_apim" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Reader"
  principal_id         = azapi_resource.apim.output.identity.principalId
}
