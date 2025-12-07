# Container App for Finance Analyst A2A Agent
# This agent uses Microsoft Agent Framework with A2A protocol
# Uses MCP Calculator, Real Estate, Government Data, Business Registry, Scratchpad, and Grounded Web Search (Bing)

resource "azapi_resource" "capp_agent_finance_analyst_a2a" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-agent-finance-analyst-a2a"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  depends_on = [
    azurerm_role_assignment.acr_pull_container_apps,
    azapi_resource.apim_mcp_calculator_api,
    azapi_resource.apim_mcp_real_estate_api,
    azapi_resource.apim_mcp_government_data_api,
    azapi_resource.apim_mcp_business_registry_api,
    azapi_resource.apim_mcp_scratchpad_api
  ]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_apps.id]
  }

  body = {
    properties = {
      managedEnvironmentId = azapi_resource.container_app_environment.id
      configuration = {
        ingress = {
          external   = true
          targetPort = 8022
          transport  = "http"
          traffic = [
            {
              latestRevision = true
              weight         = 100
            }
          ]
        }
        secrets = [
          {
            name  = "a2a-api-key"
            value = var.a2a_api_key
          },
          {
            name  = "appinsights-connection-string"
            value = azurerm_application_insights.main.connection_string
          },
          {
            name  = "mcp-auth-token"
            value = var.mcp_auth_token
          }
        ]
        registries = [
          {
            server   = azurerm_container_registry.main.login_server
            identity = azurerm_user_assigned_identity.container_apps.id
          }
        ]
      }
      template = {
        containers = [
          {
            name  = "agent-finance-analyst-a2a"
            image = local.agent_finance_analyst_a2a_image
            resources = {
              cpu    = var.agent_container_cpu
              memory = var.agent_container_memory
            }
            env = [
              # Azure OpenAI Configuration
              {
                name  = "AZURE_OPENAI_ENDPOINT"
                value = local.azure_openai_endpoint
              },
              {
                name  = "MODEL_DEPLOYMENT_NAME"
                value = var.azure_ai_model_deployment_name
              },
              {
                name  = "AZURE_OPENAI_API_VERSION"
                value = "preview"
              },
              # A2A Server Configuration
              {
                name  = "A2A_SERVER_HOST"
                value = "0.0.0.0"
              },
              {
                name  = "A2A_SERVER_PORT"
                value = "8022"
              },
              {
                name  = "A2A_PUBLIC_HOST"
                value = "ca-agent-finance-analyst-a2a.${azapi_resource.container_app_environment.output.properties.defaultDomain}"
              },
              {
                name      = "A2A_API_KEY"
                secretRef = "a2a-api-key"
              },
              # Azure Identity - use the managed identity client ID
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.container_apps.client_id
              },
              # MCP Calculator Configuration (via APIM) - primary tool
              {
                name  = "MCP_CALCULATOR_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/calculator/mcp"
              },
              {
                name      = "MCP_CALCULATOR_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # MCP Real Estate Configuration (via APIM)
              {
                name  = "MCP_REAL_ESTATE_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/real-estate/mcp"
              },
              {
                name      = "MCP_REAL_ESTATE_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # MCP Government Data Configuration (via APIM)
              {
                name  = "MCP_GOVERNMENT_DATA_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/government-data/mcp"
              },
              {
                name      = "MCP_GOVERNMENT_DATA_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # MCP Business Registry Configuration (via APIM)
              {
                name  = "MCP_BUSINESS_REGISTRY_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/business-registry/mcp"
              },
              {
                name      = "MCP_BUSINESS_REGISTRY_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # MCP Scratchpad Configuration (via APIM) - for session-scoped collaboration
              {
                name  = "MCP_SCRATCHPAD_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/scratchpad/mcp"
              },
              {
                name      = "MCP_SCRATCHPAD_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # Application Insights
              {
                name      = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                secretRef = "appinsights-connection-string"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = "/.well-known/agent-card.json"
                  port   = 8022
                  scheme = "HTTP"
                }
                initialDelaySeconds = 15
                periodSeconds       = 30
                timeoutSeconds      = 5
                failureThreshold    = 3
              },
              {
                type = "Readiness"
                httpGet = {
                  path   = "/.well-known/agent-card.json"
                  port   = 8022
                  scheme = "HTTP"
                }
                initialDelaySeconds = 10
                periodSeconds       = 10
                timeoutSeconds      = 3
                failureThreshold    = 3
              }
            ]
          }
        ]
        scale = {
          minReplicas = var.min_replicas
          maxReplicas = var.max_replicas
          rules = [
            {
              name = "http-scaling"
              http = {
                metadata = {
                  concurrentRequests = "50"
                }
              }
            }
          ]
        }
      }
    }
  }

  # Ignore case sensitivity differences in transport (Azure returns "Http" but we specify "http")
  # and memory format differences (Azure returns "1.0Gi" but we specify "1Gi")
  lifecycle {
    ignore_changes = [
      body.properties.configuration.ingress.transport,
      body.properties.template.containers[0].resources.memory
    ]
  }
}

# Output the agent's public URL
output "agent_finance_analyst_a2a_url" {
  description = "The public URL of the Finance Analyst A2A Agent"
  value       = "https://ca-agent-finance-analyst-a2a.${azapi_resource.container_app_environment.output.properties.defaultDomain}"
}

output "agent_finance_analyst_a2a_agent_card" {
  description = "The A2A Agent Card URL for discovery"
  value       = "https://ca-agent-finance-analyst-a2a.${azapi_resource.container_app_environment.output.properties.defaultDomain}/.well-known/agent-card.json"
}
