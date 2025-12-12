output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

# ACR
output "acr_name" {
  description = "ACR name"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "ACR login server"
  value       = azurerm_container_registry.main.login_server
}

# Managed identity
output "workflow_identity_client_id" {
  description = "Client ID of the workflow user-assigned managed identity"
  value       = azurerm_user_assigned_identity.workflow.client_id
}

output "workflow_identity_principal_id" {
  description = "Principal ID of the workflow user-assigned managed identity"
  value       = azurerm_user_assigned_identity.workflow.principal_id
}

# Container Apps
output "workflow_backend_url" {
  description = "Public URL for workflow backend"
  value = var.deploy_container_apps ? (
    "https://${azapi_resource.capp_workflow_backend[0].output.properties.configuration.ingress.fqdn}"
  ) : null
}

output "mcp_invoice_data_url" {
  description = "Public URL for MCP invoice data (base URL)"
  value = var.deploy_container_apps ? (
    "https://${azapi_resource.capp_mcp_invoice_data[0].output.properties.configuration.ingress.fqdn}"
  ) : null
}

# Foundry
output "ai_foundry_account_name" {
  description = "Azure AI Foundry account name"
  value       = azapi_resource.ai_foundry_account.name
}

output "ai_foundry_account_id" {
  description = "Azure AI Foundry account id"
  value       = azapi_resource.ai_foundry_account.id
}

output "ai_foundry_project_id" {
  description = "Azure AI Foundry project id"
  value       = azapi_resource.ai_foundry_project.id
}

output "ai_foundry_project_endpoint" {
  description = "Azure AI Foundry project endpoint (use as AZURE_AI_ENDPOINT)"
  value       = local.ai_foundry_project_endpoint
}

output "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = local.azure_openai_endpoint
}

output "model_gpt5_name" {
  description = "Deployment name for gpt-5"
  value       = azapi_resource.model_gpt5.name
}

output "model_gpt4o_mini_name" {
  description = "Deployment name for gpt-4o-mini"
  value       = azapi_resource.model_gpt4o_mini.name
}

# Static Web App (optional)
output "static_web_app_default_hostname" {
  description = "Static Web App hostname (if enabled)"
  value       = var.enable_static_web_app ? azapi_resource.static_web_app[0].output.properties.defaultHostname : null
}

# Static Web App name (optional)
output "static_web_app_name" {
  description = "Static Web App name (if enabled)"
  value       = var.enable_static_web_app ? azapi_resource.static_web_app[0].name : null
}
