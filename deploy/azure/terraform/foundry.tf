# ============================================================================
# Azure AI Foundry (Cognitive Services)
# ============================================================================
# Next-gen AI Foundry resource with AIServices kind for hosted agents support.
# Uses North Central US for preview feature availability.

# AI Services Account (Foundry Hub)
resource "azapi_resource" "ai_foundry_account" {
  type      = "Microsoft.CognitiveServices/accounts@2025-04-01-preview"
  name      = "ai-${var.project_name}-${random_string.suffix.result}"
  location  = var.location
  parent_id = azurerm_resource_group.main.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    properties = {
      customSubDomainName    = "ai-${var.project_name}-${random_string.suffix.result}"
      publicNetworkAccess    = "Enabled"
      disableLocalAuth       = false
      allowProjectManagement = true
    }
  }

  response_export_values = ["properties.endpoint", "properties.endpoints", "identity.principalId"]
}

# AI Foundry Project
resource "azapi_resource" "ai_foundry_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview"
  name      = "${var.project_name}-project"
  location  = var.location
  parent_id = azapi_resource.ai_foundry_account.id

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {}
  }

  response_export_values = ["properties.endpoints", "identity.principalId"]
}

# ============================================================================
# Model Deployments
# ============================================================================

# GPT-5 Model Deployment (Global Standard)
resource "azapi_resource" "model_gpt5" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview"
  name      = "gpt-5"
  parent_id = azapi_resource.ai_foundry_account.id

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = var.gpt5_capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5"
        version = "2025-08-07"
      }
      versionUpgradeOption = "OnceCurrentVersionExpired"
    }
  }

  # Deployments must be created sequentially
  depends_on = [azapi_resource.ai_foundry_project]
}

# GPT-5-mini Model Deployment (Global Standard)
resource "azapi_resource" "model_gpt5_mini" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview"
  name      = "gpt-5-mini"
  parent_id = azapi_resource.ai_foundry_account.id

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = var.gpt5_mini_capacity
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5-mini"
        version = "2025-08-07"
      }
      versionUpgradeOption = "OnceCurrentVersionExpired"
    }
  }

  # Deployments must be created sequentially
  depends_on = [azapi_resource.model_gpt5]
}

# ============================================================================
# Capability Hosts (Enable Agents)
# ============================================================================
# Capability hosts are required to enable the Agents API on Foundry projects.
# Basic setup uses Microsoft-managed storage for threads and vector stores.
# For production with your own storage, add vectorStoreConnections, 
# storageConnections, and threadStorageConnections properties.

# Account-level Capability Host
resource "azapi_resource" "ai_foundry_account_capability_host" {
  type      = "Microsoft.CognitiveServices/accounts/capabilityHosts@2025-04-01-preview"
  name      = "caphost"
  parent_id = azapi_resource.ai_foundry_account.id

  schema_validation_enabled = false

  body = {
    properties = {
      capabilityHostKind = "Agents"
    }
  }

  depends_on = [azapi_resource.model_gpt5_mini]
}

# Project-level Capability Host
resource "azapi_resource" "ai_foundry_project_capability_host" {
  type      = "Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview"
  name      = "caphostproj"
  parent_id = azapi_resource.ai_foundry_project.id

  schema_validation_enabled = false

  body = {
    properties = {
      capabilityHostKind = "Agents"
    }
  }

  depends_on = [azapi_resource.ai_foundry_account_capability_host]
}
