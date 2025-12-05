# Container App for MCP Scratchpad
resource "azapi_resource" "capp_mcp_scratchpad" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-${local.name_prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  # Ensure role assignment is complete before creating/updating
  depends_on = [azurerm_role_assignment.acr_pull_container_apps]

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
          targetPort = 8010
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
            name  = "mcp-auth-token"
            value = var.mcp_auth_token
          },
          {
            name  = "appinsights-connection-string"
            value = azurerm_application_insights.main.connection_string
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
            name  = "mcp-scratchpad"
            image = local.mcp_scratchpad_image
            resources = {
              cpu    = var.container_cpu
              memory = var.container_memory
            }
            env = [
              {
                name  = "HOST"
                value = "0.0.0.0"
              },
              {
                name  = "PORT"
                value = "8010"
              },
              {
                name      = "API_KEY"
                secretRef = "mcp-auth-token"
              },
              {
                # Required for OpenTelemetry tracing (ADR-005)
                name      = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                secretRef = "appinsights-connection-string"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = "/health"
                  port   = 8010
                  scheme = "HTTP"
                }
                initialDelaySeconds = 10
                periodSeconds       = 30
                timeoutSeconds      = 5
                failureThreshold    = 3
              },
              {
                type = "Readiness"
                httpGet = {
                  path   = "/health"
                  port   = 8010
                  scheme = "HTTP"
                }
                initialDelaySeconds = 5
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
                  concurrentRequests = "100"
                }
              }
            }
          ]
        }
      }
    }
  }

  # Ignore case sensitivity differences in transport (Azure returns "Http" but we specify "http")
  lifecycle {
    ignore_changes = [
      body.properties.configuration.ingress.transport
    ]
  }
}
