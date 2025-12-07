# Container App for Research Orchestrator API
# FastAPI-based orchestrator for multi-agent research workflows
# Coordinates A2A agents and provides SSE streaming to the web frontend

resource "azapi_resource" "capp_agent_research_orchestrator" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-research-orchestrator"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  depends_on = [
    azurerm_role_assignment.acr_pull_container_apps,
    azapi_resource.apim_mcp_scratchpad_api,
    azapi_resource.apim_mcp_demographics_api,
    azapi_resource.apim_mcp_business_registry_api,
    azapi_resource.apim_mcp_government_data_api,
    azapi_resource.apim_mcp_real_estate_api,
    azapi_resource.apim_mcp_calculator_api,
    azapi_resource.apim_api_a2a_market_analyst,
    azapi_resource.apim_api_a2a_competitor_analyst,
    azapi_resource.apim_api_a2a_finance_analyst,
    azapi_resource.apim_api_a2a_location_scout,
    azapi_resource.apim_api_a2a_synthesizer
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
          targetPort = 8000
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
            name  = "research-orchestrator"
            image = local.agent_research_orchestrator_image
            resources = {
              cpu    = var.agent_container_cpu
              memory = var.agent_container_memory
            }
            env = [
              # Azure AI Foundry Configuration
              {
                name  = "AZURE_AI_FOUNDRY_ENDPOINT"
                value = local.ai_foundry_project_endpoint
              },
              {
                name  = "MODEL_DEPLOYMENT_NAME"
                value = var.azure_ai_model_deployment_name
              },
              # Azure Identity - use the managed identity client ID
              {
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.container_apps.client_id
              },
              # MCP Scratchpad Configuration (via APIM)
              {
                name  = "MCP_SCRATCHPAD_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/scratchpad/mcp"
              },
              {
                name      = "MCP_SCRATCHPAD_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # MCP Demographics Configuration (via APIM)
              {
                name  = "MCP_DEMOGRAPHICS_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/demographics/mcp"
              },
              {
                name      = "MCP_DEMOGRAPHICS_API_KEY"
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
              # MCP Government Data Configuration (via APIM)
              {
                name  = "MCP_GOVERNMENT_DATA_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/government-data/mcp"
              },
              {
                name      = "MCP_GOVERNMENT_DATA_API_KEY"
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
              # MCP Calculator Configuration (via APIM)
              {
                name  = "MCP_CALCULATOR_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/calculator/mcp"
              },
              {
                name      = "MCP_CALCULATOR_API_KEY"
                secretRef = "mcp-auth-token"
              },
              # A2A Market Analyst Agent Configuration (via APIM)
              {
                name  = "A2A_MARKET_ANALYST_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/market-analyst"
              },
              {
                name      = "A2A_MARKET_ANALYST_API_KEY"
                secretRef = "a2a-api-key"
              },
              # A2A Competitor Analyst Agent Configuration (via APIM)
              {
                name  = "A2A_COMPETITOR_ANALYST_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/competitor-analyst"
              },
              {
                name      = "A2A_COMPETITOR_ANALYST_API_KEY"
                secretRef = "a2a-api-key"
              },
              # A2A Finance Analyst Agent Configuration (via APIM)
              {
                name  = "A2A_FINANCE_ANALYST_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/finance-analyst"
              },
              {
                name      = "A2A_FINANCE_ANALYST_API_KEY"
                secretRef = "a2a-api-key"
              },
              # A2A Location Scout Agent Configuration (via APIM)
              {
                name  = "A2A_LOCATION_SCOUT_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/location-scout"
              },
              {
                name      = "A2A_LOCATION_SCOUT_API_KEY"
                secretRef = "a2a-api-key"
              },
              # A2A Synthesizer Agent Configuration (via APIM)
              {
                name  = "A2A_SYNTHESIZER_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/synthesizer"
              },
              {
                name      = "A2A_SYNTHESIZER_API_KEY"
                secretRef = "a2a-api-key"
              },
              # Application Insights / Observability
              {
                name      = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                secretRef = "appinsights-connection-string"
              },
              {
                name  = "LOG_ANALYTICS_WORKSPACE_ID"
                value = azurerm_log_analytics_workspace.main.workspace_id
              },
              # API Configuration
              {
                name  = "API_HOST"
                value = "0.0.0.0"
              },
              {
                name  = "API_PORT"
                value = "8000"
              },
              {
                name  = "API_RELOAD"
                value = "false"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = "/health"
                  port   = 8000
                  scheme = "HTTP"
                }
                initialDelaySeconds = 15
                periodSeconds       = 30
                timeoutSeconds      = 10
                failureThreshold    = 3
              },
              {
                type = "Readiness"
                httpGet = {
                  path   = "/health"
                  port   = 8000
                  scheme = "HTTP"
                }
                initialDelaySeconds = 10
                periodSeconds       = 10
                timeoutSeconds      = 5
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

# Output the orchestrator's public URL
output "research_orchestrator_url" {
  description = "The public URL of the Research Orchestrator API"
  value       = "https://ca-research-orchestrator.${azapi_resource.container_app_environment.output.properties.defaultDomain}"
}

output "research_orchestrator_health_url" {
  description = "The health check URL for the Research Orchestrator"
  value       = "https://ca-research-orchestrator.${azapi_resource.container_app_environment.output.properties.defaultDomain}/health"
}
