# ============================================================================
# Azure API Management MCP Server Passthrough - Business Registry
# ============================================================================
# Configures APIM as an MCP server passthrough for the Business Registry service.
# This enables clients to connect to the MCP Business Registry service through APIM,
# benefiting from centralized API management, authentication, and monitoring.
#
# Architecture:
# Client -> APIM (MCP API) -> Backend -> Container App (MCP Business Registry)
#
# Key Properties (discovered via REST API 2024-10-01-preview):
# - API type: "mcp" (special MCP server passthrough type)
# - mcpProperties.endpoints.mcp.uriTemplate: "/mcp" (MCP endpoint path)
# - backendId: reference to the backend resource

# ============================================================================
# Backend - Points to MCP Business Registry Container App
# ============================================================================

resource "azapi_resource" "apim_mcp_business_registry_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-05-01"
  name      = "mcp-business-registry-backend"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      description = "Backend for MCP Business Registry service hosted on Container Apps"
      protocol    = "http"
      url         = "https://${azapi_resource.capp_mcp_business_registry.output.properties.configuration.ingress.fqdn}"
    }
  }

  depends_on = [
    azapi_resource.capp_mcp_business_registry
  ]
}

# ============================================================================
# MCP API - APIM MCP Server Passthrough
# ============================================================================
# Uses API type "mcp" with mcpProperties for MCP server passthrough functionality.
# This is a special API type introduced in API version 2024-10-01-preview.
# Schema validation disabled because azapi provider doesn't yet include MCP properties.

resource "azapi_resource" "apim_mcp_business_registry_api" {
  type                      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name                      = "business-registry"
  parent_id                 = azapi_resource.apim.id
  schema_validation_enabled = false

  body = {
    properties = {
      displayName = "MCP Business Registry"
      description = "MCP Server Passthrough for Business Registry service providing company search, profiles, financials, locations, industry players, and company news"
      path        = "business-registry"

      # MCP-specific configuration
      type      = "mcp"
      backendId = azapi_resource.apim_mcp_business_registry_backend.name

      mcpProperties = {
        endpoints = {
          mcp = {
            uriTemplate = "/mcp"
          }
        }
      }

      # API configuration
      subscriptionRequired = false
      protocols            = ["https"]
    }
  }

  depends_on = [
    azapi_resource.apim_mcp_business_registry_backend
  ]
}
