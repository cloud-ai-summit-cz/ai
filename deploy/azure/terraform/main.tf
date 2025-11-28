# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# Log Analytics Workspace for Container Apps monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.name_prefix}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# Container Apps Environment
resource "azapi_resource" "container_app_environment" {
  type      = "Microsoft.App/managedEnvironments@2024-03-01"
  name      = "cae-${local.name_prefix}-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  body = {
    properties = {
      appLogsConfiguration = {
        destination = "log-analytics"
        logAnalyticsConfiguration = {
          customerId = azurerm_log_analytics_workspace.main.workspace_id
          sharedKey  = azurerm_log_analytics_workspace.main.primary_shared_key
        }
      }
      zoneRedundant = false
    }
  }
}

# Container App for MCP Scratchpad
resource "azapi_resource" "container_app" {
  type      = "Microsoft.App/containerApps@2024-03-01"
  name      = "ca-${local.name_prefix}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  body = {
    properties = {
      managedEnvironmentId = azapi_resource.container_app_environment.id
      configuration = {
        ingress = {
          external   = true
          targetPort = 8080
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
          }
        ]
      }
      template = {
        containers = [
          {
            name  = "mcp-scratchpad"
            image = var.container_image
            resources = {
              cpu    = var.container_cpu
              memory = var.container_memory
            }
            env = [
              {
                name  = "MCP_HOST"
                value = "0.0.0.0"
              },
              {
                name  = "MCP_PORT"
                value = "8080"
              },
              {
                name  = "MCP_LOG_LEVEL"
                value = "INFO"
              },
              {
                name      = "MCP_AUTH_TOKEN"
                secretRef = "mcp-auth-token"
              }
            ]
            probes = [
              {
                type = "Liveness"
                httpGet = {
                  path   = "/health"
                  port   = 8080
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
                  port   = 8080
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
}
