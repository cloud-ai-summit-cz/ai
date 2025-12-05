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
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/business-registry/mcp"
      isSharedToAll = false
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
    azapi_resource.apim_mcp_business_registry_api
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
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/government-data/mcp"
      isSharedToAll = false
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
    azapi_resource.apim_mcp_government_data_api
  ]
}

# ============================================================================
# MCP Demographics Connection (AI Gateway Managed via APIM)
# ============================================================================
# Tools: get_population_stats, get_income_distribution, get_age_distribution,
#        get_consumer_spending, get_lifestyle_segments, get_commuter_patterns
#
# This connection routes through Azure API Management for AI Gateway governance.
# Key differences from direct Container App connections:
# - target: Points to APIM gateway URL instead of direct Container App
# - ApiType: "Azure" indicates AI Gateway managed (shows in Foundry UI)
# - Authentication flows through APIM subscription key

resource "azapi_resource" "mcp_connection_demographics" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-demographics"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/demographics/mcp"
      isSharedToAll = false
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
    azapi_resource.apim_mcp_demographics_api
  ]
}

# ============================================================================
# MCP Real Estate Connection
# ============================================================================
# Tools: search_commercial_properties, get_rental_rates, get_foot_traffic,
#        get_nearby_amenities, get_location_score, get_vacancy_rates,
#        compare_locations

resource "azapi_resource" "mcp_connection_real_estate" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-real-estate"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/real-estate/mcp"
      isSharedToAll = false
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "real-estate"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.apim_mcp_real_estate_api
  ]
}

# ============================================================================
# MCP Calculator Connection
# ============================================================================
# Tools: calculate_startup_costs, calculate_operating_costs, project_revenue,
#        calculate_break_even, calculate_roi, project_cash_flow,
#        calculate_npv, sensitivity_analysis

resource "azapi_resource" "mcp_connection_calculator" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-calculator"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/calculator/mcp"
      isSharedToAll = false
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "calculator"
      }
    }
  }

  depends_on = [
    azapi_resource.ai_foundry_project_capability_host,
    azapi_resource.apim_mcp_calculator_api
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
      target        = "${azapi_resource.apim.output.properties.gatewayUrl}/scratchpad/mcp"
      isSharedToAll = false
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
    azapi_resource.apim_mcp_scratchpad_api
  ]
}
