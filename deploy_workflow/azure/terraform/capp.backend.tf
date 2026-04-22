resource "azapi_resource" "capp_workflow_backend" {
  count     = var.deploy_container_apps ? 1 : 0
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-workflow-backend"
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
          external   = true
          targetPort = var.bootstrap_with_hello_world ? 80 : 8000
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
            name  = "workflow-backend"
            image = local.workflow_backend_image
            resources = {
              cpu    = var.backend_container_cpu
              memory = var.backend_container_memory
            }
            env = [
              {
                name  = "HOST"
                value = "0.0.0.0"
              },
              {
                name  = "PORT"
                value = "8000"
              },
              {
                # Backend requires project endpoint
                name  = "AZURE_AI_ENDPOINT"
                value = local.ai_foundry_project_endpoint
              },
              {
                # Ensure DefaultAzureCredential selects this UAMI
                name  = "AZURE_CLIENT_ID"
                value = azurerm_user_assigned_identity.workflow.client_id
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
                  port   = var.bootstrap_with_hello_world ? 80 : 8000
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
                  path   = var.bootstrap_with_hello_world ? "/" : "/health"
                  port   = var.bootstrap_with_hello_world ? 80 : 8000
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
