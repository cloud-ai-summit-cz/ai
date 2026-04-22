# Container App for Web Research UI
# React-based frontend for the research workflow
# Uses nginx to serve static files and connects to the research orchestrator API

resource "azapi_resource" "capp_web_research" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-web-research"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  depends_on = [
    azurerm_role_assignment.acr_pull_container_apps,
    azapi_resource.capp_agent_research_orchestrator
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
          targetPort = 80
          transport  = "http"
          traffic = [
            {
              latestRevision = true
              weight         = 100
            }
          ]
        }
        secrets = []
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
            name  = "web-research"
            image = local.web_research_image
            resources = {
              cpu    = var.container_cpu
              memory = var.container_memory
            }
            env = [
              # API URL - points to the research orchestrator via APIM
              # The env.sh script at container startup writes this to /usr/share/nginx/html/config.js
              {
                name  = "VITE_API_URL"
                value = "${azapi_resource.apim.output.properties.gatewayUrl}/orchestrator"
              },
              # App version for display
              {
                name  = "APP_VERSION"
                value = "1.0.0"
              },
              # Disable mock mode in production
              {
                name  = "ENABLE_MOCK"
                value = "false"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = "/health"
                  port   = 80
                  scheme = "HTTP"
                }
                initialDelaySeconds = 5
                periodSeconds       = 30
                timeoutSeconds      = 5
                failureThreshold    = 3
              },
              {
                type = "Readiness"
                httpGet = {
                  path   = "/health"
                  port   = 80
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
  # and memory format differences (Azure returns "1.0Gi" but we specify "1Gi")
  lifecycle {
    ignore_changes = [
      body.properties.configuration.ingress.transport,
      body.properties.template.containers[0].resources.memory
    ]
  }
}

# Output the web UI's public URL
output "web_research_url" {
  description = "The public URL of the Web Research UI"
  value       = "https://ca-web-research.${azapi_resource.container_app_environment.output.properties.defaultDomain}"
}
