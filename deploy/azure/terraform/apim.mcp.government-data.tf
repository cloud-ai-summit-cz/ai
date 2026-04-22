# ============================================================================
# Azure API Management MCP Server Passthrough - Government Data
# ============================================================================
# Configures APIM as an MCP server passthrough for the Government Data service.
# This enables clients to connect to the MCP Government Data service through APIM,
# benefiting from centralized API management, authentication, and monitoring.
#
# Architecture:
# Client -> APIM (MCP API) -> Backend -> Container App (MCP Government Data)
#
# Key Properties (discovered via REST API 2024-10-01-preview):
# - API type: "mcp" (special MCP server passthrough type)
# - mcpProperties.endpoints.mcp.uriTemplate: "/mcp" (MCP endpoint path)
# - backendId: reference to the backend resource

# ============================================================================
# Backend - Points to MCP Government Data Container App
# ============================================================================

resource "azapi_resource" "apim_mcp_government_data_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-05-01"
  name      = "mcp-government-data-backend"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      description = "Backend for MCP Government Data service hosted on Container Apps"
      protocol    = "http"
      url         = "https://${azapi_resource.capp_mcp_government_data.output.properties.configuration.ingress.fqdn}"
    }
  }

  depends_on = [
    azapi_resource.capp_mcp_government_data
  ]
}

# ============================================================================
# MCP API - APIM MCP Server Passthrough
# ============================================================================
# Uses API type "mcp" with mcpProperties for MCP server passthrough functionality.
# This is a special API type introduced in API version 2024-10-01-preview.
# Schema validation disabled because azapi provider doesn't yet include MCP properties.

resource "azapi_resource" "apim_mcp_government_data_api" {
  type                      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name                      = "government-data"
  parent_id                 = azapi_resource.apim.id
  schema_validation_enabled = false

  body = {
    properties = {
      displayName = "MCP Government Data"
      description = "MCP Server Passthrough for Government Data service providing business permits, zoning info, regulations, tax rates, licensing requirements, health safety codes, and labor laws"
      path        = "government-data"

      # MCP-specific configuration
      type      = "mcp"
      backendId = azapi_resource.apim_mcp_government_data_backend.name

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
    azapi_resource.apim_mcp_government_data_backend
  ]
}

# ============================================================================
# MCP API Policy
# ============================================================================
# Configures timeout and buffering policies for the MCP service.
# Extended timeout to handle long-running operations (max effective ~230s
# due to Azure Load Balancer 4-minute idle connection limit).

resource "azapi_resource" "apim_mcp_government_data_policy" {
  type      = "Microsoft.ApiManagement/service/apis/policies@2024-10-01-preview"
  name      = "policy"
  parent_id = azapi_resource.apim_mcp_government_data_api.id

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
