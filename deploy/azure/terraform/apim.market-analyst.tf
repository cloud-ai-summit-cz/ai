# ============================================================================
# Azure API Management - A2A Agent: Market Analyst
# ============================================================================
# Registers the Market Analyst agent as an A2A (Agent-to-Agent) API in APIM.
# This enables the agent to be discovered and invoked through the AI Gateway.
#
# A2A agents use JSON-RPC protocol for communication and expose an agent card
# at a well-known endpoint for capability discovery.
#
# API Version: 2024-10-01-preview (required for A2A/isAgent properties)

# ============================================================================
# Local Variables for Market Analyst Agent
# ============================================================================

locals {
  # Agent configuration
  market_analyst_agent_id   = "market-analyst"
  market_analyst_agent_name = "market-analyst"

  # Backend URL from Container App (the actual agent endpoint)
  market_analyst_backend_url = "https://${azapi_resource.capp_agent_market_analyst_a2a.output.properties.configuration.ingress.fqdn}"
}

# ============================================================================
# A2A Agent API Definition
# ============================================================================
# Creates an A2A type API in APIM with agent-specific properties.
# Key properties:
# - type: "a2a" - marks this as an Agent-to-Agent protocol API
# - isAgent: true - indicates this API represents an AI agent
# - a2aProperties: configures the agent card endpoint for discovery
# - jsonRpcProperties: configures the JSON-RPC backend endpoint

resource "azapi_resource" "apim_api_a2a_market_analyst" {
  type      = "Microsoft.ApiManagement/service/apis@2024-10-01-preview"
  name      = "${local.market_analyst_agent_id}-${random_string.suffix.result}"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      displayName = local.market_analyst_agent_name
      description = ""
      path        = local.market_analyst_agent_name
      protocols   = ["https"]

      # A2A specific configuration
      type    = "a2a"
      isAgent = true

      # Agent metadata for discovery
      agent = {
        id                  = local.market_analyst_agent_id
        name                = local.market_analyst_agent_name
        managementPortalUrl = ""
        providerName        = null
      }

      # A2A properties for agent card discovery
      a2aProperties = {
        agentCardBackendUrl = "${local.market_analyst_backend_url}/.well-known/agent-card.json"
        agentCardPath       = "/agent-card.json"
      }

      # JSON-RPC backend configuration
      jsonRpcProperties = {
        backendUrl = local.market_analyst_backend_url
        path       = "/"
      }

      # Subscription not required for A2A agents (authentication handled differently)
      subscriptionRequired = false
      subscriptionKeyParameterNames = {
        header = "Ocp-Apim-Subscription-Key"
        query  = "subscription-key"
      }

      # Standard API settings
      apiRevision = "1"
      serviceUrl  = ""
      authenticationSettings = {
        oAuth2                          = null
        oAuth2AuthenticationSettings    = []
        openid                          = null
        openidAuthenticationSettings    = []
        returnProtectedResourceMetadata = false
      }
    }
  }

  schema_validation_enabled = false

  depends_on = [
    azapi_resource.apim,
    azapi_resource.capp_agent_market_analyst_a2a
  ]
}

# ============================================================================
# A2A Agent Operations
# ============================================================================
# A2A agents expose all HTTP methods with wildcard URL template (/*) to support
# the full JSON-RPC protocol and agent card discovery.

resource "azapi_resource" "apim_operation_a2a_market_analyst_get" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "get"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "GET"
      method             = "GET"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_post" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "post"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "POST"
      method             = "POST"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_put" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "put"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "PUT"
      method             = "PUT"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_delete" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "delete"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "DELETE"
      method             = "DELETE"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_patch" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "patch"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "PATCH"
      method             = "PATCH"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_head" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "head"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "HEAD"
      method             = "HEAD"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

resource "azapi_resource" "apim_operation_a2a_market_analyst_options" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-10-01-preview"
  name      = "options"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

  body = {
    properties = {
      displayName        = "OPTIONS"
      method             = "OPTIONS"
      urlTemplate        = "/*"
      description        = null
      responses          = []
      templateParameters = []
    }
  }
}

# ============================================================================
# A2A Agent API Policy
# ============================================================================
# Configures CORS and other policies for the A2A agent.
# The CORS policy allows cross-origin requests from the requesting origin.

resource "azapi_resource" "apim_api_a2a_market_analyst_policy" {
  type      = "Microsoft.ApiManagement/service/apis/policies@2024-10-01-preview"
  name      = "policy"
  parent_id = azapi_resource.apim_api_a2a_market_analyst.id

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
    <base />
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
    azapi_resource.apim_operation_a2a_market_analyst_get,
    azapi_resource.apim_operation_a2a_market_analyst_post,
    azapi_resource.apim_operation_a2a_market_analyst_put,
    azapi_resource.apim_operation_a2a_market_analyst_delete,
    azapi_resource.apim_operation_a2a_market_analyst_patch,
    azapi_resource.apim_operation_a2a_market_analyst_head,
    azapi_resource.apim_operation_a2a_market_analyst_options
  ]
}
