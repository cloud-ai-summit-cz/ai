locals {
  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  workflow_backend_image = (
    var.workflow_backend_image != ""
    ? var.workflow_backend_image
    : (
      var.bootstrap_with_hello_world
      ? "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      : "${azurerm_container_registry.main.login_server}/workflow-backend:latest"
    )
  )

  mcp_invoice_data_image = (
    var.mcp_invoice_data_image != ""
    ? var.mcp_invoice_data_image
    : (
      var.bootstrap_with_hello_world
      ? "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      : "${azurerm_container_registry.main.login_server}/mcp-invoice-data:latest"
    )
  )

  ai_foundry_endpoint = azapi_resource.ai_foundry_account.output.properties.endpoint

  ai_foundry_project_endpoint = "https://ai-${var.project_name}-${random_string.suffix.result}.services.ai.azure.com/api/projects/${var.project_name}-project"

  azure_openai_endpoint = "https://ai-${var.project_name}-${random_string.suffix.result}.openai.azure.com/"

  ai_foundry_account_principal_id = azapi_resource.ai_foundry_account.output.identity.principalId
  ai_foundry_project_principal_id = azapi_resource.ai_foundry_project.output.identity.principalId
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}
