# ============================================================================
# Azure API Management MCP Server Passthrough - Real Estate
# ============================================================================
# Configures APIM as an MCP server passthrough for the Real Estate service.
# This enables clients to connect to the MCP Real Estate service through APIM,
# benefiting from centralized API management, authentication, and monitoring.
#
# Architecture:
# Client -> APIM (MCP API) -> Backend -> Container App (MCP Real Estate)
#
# Key Properties (discovered via REST API 2024-10-01-preview):
# - API type: "mcp" (special MCP server passthrough type)
# - mcpProperties.endpoints.mcp.uriTemplate: "/mcp" (MCP endpoint path)
# - backendId: reference to the backend resource

# ============================================================================
# Backend - Points to MCP Real Estate Container App
# ============================================================================

resource "azapi_resource" "apim_mcp_real_estate_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-05-01"
  name      = "mcp-real-estate-backend"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      description = "Backend for MCP Real Estate service hosted on Container Apps"
      protocol    = "http"
      url         = "https://${azapi_resource.capp_mcp_real_estate.output.properties.configuration.ingress.fqdn}"
    }
  }

  depends_on = [
    azapi_resource.capp_mcp_real_estate
  ]
}

# ============================================================================
# MCP API - APIM MCP Server Passthrough
# ============================================================================
# Uses API type "mcp" with mcpProperties for MCP server passthrough functionality.
# This is a special API type introduced in API version 2024-10-01-preview.
# Schema validation disabled because azapi provider doesn't yet include MCP properties.

resource "azapi_resource" "apim_mcp_real_estate_api" {
  type                      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name                      = "real-estate"
  parent_id                 = azapi_resource.apim.id
  schema_validation_enabled = false

  body = {
    properties = {
      displayName = "MCP Real Estate"
      description = "MCP Server Passthrough for Real Estate service providing commercial property search, rental rates, foot traffic, nearby amenities, location scores, vacancy rates, and location comparisons"
      path        = "real-estate"

      # MCP-specific configuration
      type      = "mcp"
      backendId = azapi_resource.apim_mcp_real_estate_backend.name

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
    azapi_resource.apim_mcp_real_estate_backend
  ]
}

# ============================================================================
# MCP API Policy
# ============================================================================
# Configures timeout and buffering policies for the MCP service.
# Extended timeout to handle long-running operations (max effective ~230s
# due to Azure Load Balancer 4-minute idle connection limit).

resource "azapi_resource" "apim_mcp_real_estate_policy" {
  type      = "Microsoft.ApiManagement/service/apis/policies@2024-10-01-preview"
  name      = "policy"
  parent_id = azapi_resource.apim_mcp_real_estate_api.id

  body = {
    properties = {
      format = "xml"
      value  = <<-XML
<policies>
  <inbound>
    <base />
  </inbound>
  <backend>
    <!-- Extended timeout (230s max effective due to Azure LB 4-min idle limit) -->
    <!-- buffer-response=false allows streaming/keepalive data to flow through -->
    <forward-request timeout="230" buffer-response="false" />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
      XML
    }
  }

  # Ignore XML whitespace normalization differences
  lifecycle {
    ignore_changes = [
      body.properties.value
    ]
  }
}
