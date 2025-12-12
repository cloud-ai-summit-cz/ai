resource "azapi_resource" "capp_mcp_invoice_data" {
  count     = var.deploy_container_apps ? 1 : 0
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-mcp-invoice-data"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  depends_on = [azurerm_role_assignment.acr_push_workflow_identity]

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.workflow.id]
  }

  body = {
    properties = {
      managedEnvironmentId = azapi_resource.container_app_environment.id
      configuration = {
        ingress = {
          # Keep external so Foundry/agents can reach it as an MCP endpoint.
          external   = true
          targetPort = var.bootstrap_with_hello_world ? 80 : 8014
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
            name  = "mcp-api-key"
            value = var.mcp_invoice_api_key
          },
          {
            name  = "appinsights-connection-string"
            value = azurerm_application_insights.main.connection_string
          }
        ]
        registries = [
          {
            server   = azurerm_container_registry.main.login_server
            identity = azurerm_user_assigned_identity.workflow.id
          }
        ]
      }
      template = {
        containers = [
          {
            name  = "mcp-invoice-data"
            image = local.mcp_invoice_data_image
            resources = {
              cpu    = var.mcp_container_cpu
              memory = var.mcp_container_memory
            }
            env = [
              {
                name  = "HOST"
                value = "0.0.0.0"
              },
              {
                name  = "PORT"
                value = "8014"
              },
              {
                name      = "API_KEY"
                secretRef = "mcp-api-key"
              },
              {
                name      = "APPLICATIONINSIGHTS_CONNECTION_STRING"
                secretRef = "appinsights-connection-string"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = var.bootstrap_with_hello_world ? "/" : "/health"
                  port   = var.bootstrap_with_hello_world ? 80 : 8014
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
                  path   = var.bootstrap_with_hello_world ? "/" : "/ready"
                  port   = var.bootstrap_with_hello_world ? 80 : 8014
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

  lifecycle {
    ignore_changes = [
      body.properties.configuration.ingress.transport
    ]
  }
}
