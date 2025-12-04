# ============================================================================
# Azure API Management (Standard v2)
# ============================================================================
# API Management instance for AI Gateway integration with Azure AI Foundry.
# Uses Standard v2 tier as required for Foundry Agents APIM connection.
# Provides centralized API management, rate limiting, and security for AI models.

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
# APIM Subscription Key Generation
# ============================================================================
# Generate a random key for the APIM subscription. The APIM API does not return
# subscription keys in GET responses - you need to call /listSecrets POST.
# To avoid this complexity, we generate our own key and pass it during creation.

resource "random_password" "apim_subscription_key" {
  length  = 32
  special = false
}

# ============================================================================
# APIM Subscription for Agent Access
# ============================================================================
# Creates a subscription key for Foundry agents to authenticate with APIM.
# This subscription is scoped to all APIs for simplicity.

resource "azapi_resource" "apim_subscription_agents" {
  type      = "Microsoft.ApiManagement/service/subscriptions@2024-05-01"
  name      = "foundry-agents"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      displayName  = "Foundry Agents Subscription"
      scope        = "/apis"
      allowTracing = true
      state        = "active"
      primaryKey   = random_password.apim_subscription_key.result
    }
  }
}

# ============================================================================
# Azure OpenAI API Import
# ============================================================================
# Imports the Azure OpenAI API specification into APIM for proxying requests.
# Uses the standard Azure OpenAI API specification format.

resource "azapi_resource" "apim_api_aoai" {
  type      = "Microsoft.ApiManagement/service/apis@2024-05-01"
  name      = "azure-openai"
  parent_id = azapi_resource.apim.id

  body = {
    properties = {
      displayName          = "Azure OpenAI Service API"
      description          = "Azure OpenAI APIs for chat completions and model access"
      path                 = "openai"
      protocols            = ["https"]
      subscriptionRequired = true
      subscriptionKeyParameterNames = {
        header = "api-key"
        query  = "subscription-key"
      }
      serviceUrl = local.azure_openai_endpoint
      apiType    = "http"
    }
  }

  depends_on = [azapi_resource.apim]
}

# ============================================================================
# Chat Completions Operation
# ============================================================================
# Adds the chat/completions endpoint for model inference.

resource "azapi_resource" "apim_operation_chat_completions" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-05-01"
  name      = "chat-completions"
  parent_id = azapi_resource.apim_api_aoai.id

  body = {
    properties = {
      displayName = "Creates a completion for the chat message"
      method      = "POST"
      urlTemplate = "/deployments/{deployment-id}/chat/completions"
      description = "Creates a model response for the given chat conversation."
      templateParameters = [
        {
          name        = "deployment-id"
          description = "Deployment id of the model which was deployed."
          type        = "string"
          required    = true
        }
      ]
      request = {
        queryParameters = [
          {
            name         = "api-version"
            description  = "The API version to use for this operation."
            type         = "string"
            required     = true
            defaultValue = "2024-02-01"
          }
        ]
      }
      responses = [
        {
          statusCode  = 200
          description = "OK"
        }
      ]
    }
  }
}

# ============================================================================
# List Deployments Operation (for Dynamic Model Discovery)
# ============================================================================
# Adds the /deployments endpoint for Foundry Agents to discover available models.

resource "azapi_resource" "apim_operation_list_deployments" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-05-01"
  name      = "list-deployments"
  parent_id = azapi_resource.apim_api_aoai.id

  body = {
    properties = {
      displayName = "List Deployments"
      method      = "GET"
      urlTemplate = "/deployments"
      description = "Gets the list of deployments."
      responses = [
        {
          statusCode  = 200
          description = "OK"
        }
      ]
    }
  }
}

# ============================================================================
# Get Deployment Operation (for Dynamic Model Discovery)
# ============================================================================
# Adds the /deployments/{deploymentName} endpoint for getting specific deployment details.

resource "azapi_resource" "apim_operation_get_deployment" {
  type      = "Microsoft.ApiManagement/service/apis/operations@2024-05-01"
  name      = "get-deployment"
  parent_id = azapi_resource.apim_api_aoai.id

  body = {
    properties = {
      displayName = "Get Deployment"
      method      = "GET"
      urlTemplate = "/deployments/{deployment-id}"
      description = "Gets info about a deployment."
      templateParameters = [
        {
          name        = "deployment-id"
          description = "The deployment id"
          type        = "string"
          required    = true
        }
      ]
      responses = [
        {
          statusCode  = 200
          description = "OK"
        }
      ]
    }
  }
}

# ============================================================================
# API Policy - Backend Service and Authentication
# ============================================================================
# Configures APIM to forward requests to Azure OpenAI with managed identity auth.

resource "azapi_resource" "apim_api_policy" {
  type      = "Microsoft.ApiManagement/service/apis/policies@2024-05-01"
  name      = "policy"
  parent_id = azapi_resource.apim_api_aoai.id

  body = {
    properties = {
      format = "xml"
      value  = <<-XML
        <policies>
          <inbound>
            <base />
            <set-backend-service base-url="${local.azure_openai_endpoint}" />
            <authentication-managed-identity resource="https://cognitiveservices.azure.com/" />
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
    azapi_resource.apim_operation_chat_completions,
    azapi_resource.apim_operation_list_deployments,
    azapi_resource.apim_operation_get_deployment
  ]
}

# ============================================================================
# List Deployments Policy (ARM Management API)
# ============================================================================
# Policy to route list deployments requests to Azure Resource Manager.

resource "azapi_resource" "apim_operation_list_deployments_policy" {
  type      = "Microsoft.ApiManagement/service/apis/operations/policies@2024-05-01"
  name      = "policy"
  parent_id = azapi_resource.apim_operation_list_deployments.id

  body = {
    properties = {
      format = "xml"
      value  = <<-XML
        <policies>
          <inbound>
            <base />
            <authentication-managed-identity resource="https://management.azure.com/" />
            <rewrite-uri template="/deployments?api-version=2023-05-01" copy-unmatched-params="false" />
            <set-backend-service base-url="https://management.azure.com${azapi_resource.ai_foundry_account.id}" />
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
}

# ============================================================================
# Get Deployment Policy (ARM Management API)
# ============================================================================
# Policy to route get deployment requests to Azure Resource Manager.

resource "azapi_resource" "apim_operation_get_deployment_policy" {
  type      = "Microsoft.ApiManagement/service/apis/operations/policies@2024-05-01"
  name      = "policy"
  parent_id = azapi_resource.apim_operation_get_deployment.id

  body = {
    properties = {
      format = "rawxml"
      value  = <<-XML
<policies>
  <inbound>
    <base />
    <authentication-managed-identity resource="https://management.azure.com/" />
    <set-variable name="deploymentId" value="@(context.Request.MatchedParameters.GetValueOrDefault(&quot;deployment-id&quot;,&quot;&quot;))" />
    <rewrite-uri template="@{return &quot;/deployments/&quot; + (string)context.Variables[&quot;deploymentId&quot;] + &quot;?api-version=2023-05-01&quot;;}" copy-unmatched-params="false" />
    <set-backend-service base-url="https://management.azure.com${azapi_resource.ai_foundry_account.id}" />
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
