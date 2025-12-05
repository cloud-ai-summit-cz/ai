# ============================================================================
# Azure API Management MCP Server Passthrough - Calculator
# ============================================================================
# Configures APIM as an MCP server passthrough for the Calculator service.
# This enables clients to connect to the MCP Calculator service through APIM,
# benefiting from centralized API management, authentication, and monitoring.
#
# Architecture:
# Client -> APIM (MCP API) -> Backend -> Container App (MCP Calculator)
#
# Key Properties (discovered via REST API 2024-10-01-preview):
# - API type: "mcp" (special MCP server passthrough type)
# - mcpProperties.endpoints.mcp.uriTemplate: "/mcp" (MCP endpoint path)
# - backendId: reference to the backend resource

# ============================================================================
# Backend - Points to MCP Calculator Container App
# ============================================================================

resource "azapi_resource" "apim_mcp_calculator_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-05-01"
  name      = "mcp-calculator-backend"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      description = "Backend for MCP Calculator service hosted on Container Apps"
      protocol    = "http"
      url         = "https://${azapi_resource.capp_mcp_calculator.output.properties.configuration.ingress.fqdn}"
    }
  }

  depends_on = [
    azapi_resource.capp_mcp_calculator
  ]
}

# ============================================================================
# MCP API - APIM MCP Server Passthrough
# ============================================================================
# Uses API type "mcp" with mcpProperties for MCP server passthrough functionality.
# This is a special API type introduced in API version 2024-10-01-preview.
# Schema validation disabled because azapi provider doesn't yet include MCP properties.

resource "azapi_resource" "apim_mcp_calculator_api" {
  type                      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name                      = "calculator"
  parent_id                 = azapi_resource.apim.id
  schema_validation_enabled = false

  body = {
    properties = {
      displayName = "MCP Calculator"
      description = "MCP Server Passthrough for Calculator service providing startup cost calculations, operating costs, revenue projections, break-even analysis, ROI calculations, cash flow projections, NPV calculations, and sensitivity analysis"
      path        = "calculator"

      # MCP-specific configuration
      type      = "mcp"
      backendId = azapi_resource.apim_mcp_calculator_backend.name

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
    azapi_resource.apim_mcp_calculator_backend
  ]
}
