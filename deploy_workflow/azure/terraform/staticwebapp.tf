# ==========================================================================
# Azure Static Web App (optional)
# ==========================================================================
resource "azapi_resource" "static_web_app" {
  count     = var.enable_static_web_app ? 1 : 0
  type      = "Microsoft.Web/staticSites@2023-12-01"
  name      = "${var.swa_name}-${random_string.suffix.result}"
  location  = azurerm_resource_group.main.location
  parent_id = azurerm_resource_group.main.id
  tags      = local.common_tags

  schema_validation_enabled = false

  body = {
    sku = {
      name = "Standard"
    }
    properties = merge(
      {
        buildProperties = {
          appLocation    = "src/workflows/frontend"
          apiLocation    = ""
          outputLocation = ""
        }
      },
      (var.swa_repo_url != "" && var.swa_github_token != "") ? {
        repositoryUrl   = var.swa_repo_url
        branch          = var.swa_branch
        repositoryToken = var.swa_github_token
      } : {}
    )
  }

  response_export_values = ["properties.defaultHostname"]

}
