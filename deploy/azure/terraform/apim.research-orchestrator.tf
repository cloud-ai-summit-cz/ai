# ============================================================================
# Azure API Management - Research Orchestrator API
# ============================================================================
# Registers the Research Orchestrator as a standard HTTP API in APIM.
# This enables the web frontend to access the orchestrator through APIM,
# benefiting from centralized API management, CORS handling, and monitoring.
#
# Architecture:
# Web UI -> APIM (Orchestrator API) -> Backend -> Container App (Research Orchestrator)

# ============================================================================
# Backend - Points to Research Orchestrator Container App
# ============================================================================

resource "azapi_resource" "apim_research_orchestrator_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-05-01"
  name      = "research-orchestrator-backend"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      description = "Backend for Research Orchestrator FastAPI service hosted on Container Apps"
      protocol    = "http"
      url         = "https://${azapi_resource.capp_agent_research_orchestrator.output.properties.configuration.ingress.fqdn}"
    }
  }

  depends_on = [
    azapi_resource.capp_agent_research_orchestrator
  ]
}

# ============================================================================
# HTTP API - Standard REST API for Research Orchestrator
# ============================================================================
# Standard HTTP API with wildcard operations to support all REST endpoints
# and SSE streaming for real-time updates.

resource "azapi_resource" "apim_research_orchestrator_api" {
  type                      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name                      = "orchestrator"
  parent_id                 = azapi_resource.apim.id
  schema_validation_enabled = false

  body = {
    properties = {
      displayName = "Research Orchestrator"
      description = "REST API for the Research Orchestrator service providing research session management and SSE streaming"
      path        = "orchestrator"
      protocols   = ["https"]
      type        = "http"

      # Service URL points to the backend
      serviceUrl = "https://${azapi_resource.capp_agent_research_orchestrator.output.properties.configuration.ingress.fqdn}"

      # No subscription required for this internal API
      subscriptionRequired = false
      subscriptionKeyParameterNames = {
        header = "Ocp-Apim-Subscription-Key"
        query  = "subscription-key"
      }

      # Standard API settings
      apiRevision = "1"
      authenticationSettings = {
        oAuth2                          = null
        oAuth2AuthenticationSettings    = []
        openid                          = null
        openidAuthenticationSettings    = []
        returnProtectedResourceMetadata = false
      }
    }
  }

  depends_on = [
    azapi_resource.apim_research_orchestrator_backend
  ]
}

# ============================================================================
# API Operations - All HTTP Methods with Wildcard URL
# ============================================================================
# Support all HTTP methods to enable full REST API access and SSE streaming.

resource "azapi_resource" "apim_operation_orchestrator_get" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "get"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "GET"
      method             = "GET"
      urlTemplate        = "/*"
      description        = "GET operations including SSE streaming endpoints"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_post" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "post"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "POST"
      method             = "POST"
      urlTemplate        = "/*"
      description        = "POST operations for session creation and research submission"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_put" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "put"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "PUT"
      method             = "PUT"
      urlTemplate        = "/*"
      description        = "PUT operations"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_delete" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "delete"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "DELETE"
      method             = "DELETE"
      urlTemplate        = "/*"
      description        = "DELETE operations for session cleanup"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_patch" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "patch"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "PATCH"
      method             = "PATCH"
      urlTemplate        = "/*"
      description        = "PATCH operations"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_head" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "head"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "HEAD"
      method             = "HEAD"
      urlTemplate        = "/*"
      description        = "HEAD operations"
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_orchestrator_options" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "options"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      displayName        = "OPTIONS"
      method             = "OPTIONS"
      urlTemplate        = "/*"
      description        = "OPTIONS operations for CORS preflight"
      responses          = []
      templateParameters = []
    }
  }
}

# ============================================================================
# API Policy - CORS and Streaming Support
# ============================================================================
# Configures CORS policy for cross-origin requests from the web UI
# and extended timeout with buffer-response=false for SSE streaming.

resource "azapi_resource" "apim_research_orchestrator_policy" {
  type      = "Microsoft.ApiManagement/service/apis/policies@2024-10-01-preview"
  name      = "policy"
  parent_id = azapi_resource.apim_research_orchestrator_api.id

  body = {
    properties = {
      format = "xml"
      value  = <<-XML
<policies>
  <inbound>
    <base />
    <cors allow-credentials="true">
      <allowed-origins>
        <origin>@(context.Request.Headers.GetValueOrDefault("Origin") ?? $"https://{context.Request.Url.Host}")</origin>
      </allowed-origins>
      <allowed-methods>
        <method>*</method>
      </allowed-methods>
      <allowed-headers>
        <header>*</header>
      </allowed-headers>
      <expose-headers>
        <header>*</header>
      </expose-headers>
    </cors>
  </inbound>
  <backend>
    <!-- Extended timeout (230s max effective due to Azure LB 4-min idle limit) -->
    <!-- buffer-response=false is CRITICAL for SSE streaming to work -->
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

  depends_on = [
    azapi_resource.apim_operation_orchestrator_get,
    azapi_resource.apim_operation_orchestrator_post,
    azapi_resource.apim_operation_orchestrator_put,
    azapi_resource.apim_operation_orchestrator_delete,
    azapi_resource.apim_operation_orchestrator_patch,
    azapi_resource.apim_operation_orchestrator_head,
    azapi_resource.apim_operation_orchestrator_options
  ]

  # Ignore XML whitespace normalization differences
  lifecycle {
    ignore_changes = [
      body.properties.value
    ]
  }
}
