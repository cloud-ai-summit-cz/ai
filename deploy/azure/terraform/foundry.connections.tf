# ============================================================================
# Azure AI Foundry Project Connections for MCP Tools
# ============================================================================
# These connections store MCP server endpoints and authentication credentials
# securely in Azure AI Foundry, enabling agents to use MCP tools via
# project_connection_id instead of passing headers directly.
#
# Category "RemoteTool" identifies these as MCP tool connections.
# AuthType "CustomKeys" stores the Bearer token for API key authentication.

# ============================================================================
# MCP Business Registry Connection
# ============================================================================
# Tools: search_companies, get_company_profile, get_company_financials,
#        get_company_locations, get_industry_players, get_company_news

resource "azapi_resource" "mcp_connection_business_registry" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-business-registry"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "https://${azapi_resource.capp_mcp_business_registry.output.properties.configuration.ingress.fqdn}/mcp"
      isSharedToAll = true
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "business-registry"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.capp_mcp_business_registry
  ]
}

# ============================================================================
# MCP Government Data Connection
# ============================================================================
# Tools: get_business_permits, get_zoning_info, get_regulations,
#        get_tax_rates, get_licensing_requirements, get_health_safety_codes,
#        get_labor_laws

resource "azapi_resource" "mcp_connection_government_data" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-government-data"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "https://${azapi_resource.capp_mcp_government_data.output.properties.configuration.ingress.fqdn}/mcp"
      isSharedToAll = true
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "government-data"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.capp_mcp_government_data
  ]
}

# ============================================================================
# MCP Demographics Connection
# ============================================================================
# Tools: get_population_stats, get_income_distribution, get_age_distribution,
#        get_consumer_spending, get_lifestyle_segments, get_commuter_patterns

resource "azapi_resource" "mcp_connection_demographics" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-demographics"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "https://${azapi_resource.capp_mcp_demographics.output.properties.configuration.ingress.fqdn}/mcp"
      isSharedToAll = true
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "demographics"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.capp_mcp_demographics
  ]
}

# ============================================================================
# MCP Scratchpad Connection
# ============================================================================
# Tools: write_note, read_note, list_notes, delete_note, write_draft_section,
#        read_draft_section, list_draft_sections, clear_scratchpad
#
# Note: Scratchpad requires session-specific headers (X-Session-Id) for
# multi-tenant isolation. The connection stores the base auth, but sessions
# must be managed at runtime. This connection enables UI visibility while
# session headers are added dynamically by agents.

resource "azapi_resource" "mcp_connection_scratchpad" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-scratchpad"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "https://${azapi_resource.capp_mcp_scratchpad.output.properties.configuration.ingress.fqdn}/mcp"
      isSharedToAll = true
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "scratchpad"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.capp_mcp_scratchpad
  ]
}
