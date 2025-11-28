locals {
  # Resource naming prefix
  name_prefix = "mcp-scratchpad"

  # Common tags applied to all resources
  common_tags = {
    Project   = "mcp-scratchpad"
    ManagedBy = "terraform"
  }

  # Container images - use ACR if variable is empty, otherwise use provided value
  mcp_scratchpad_image = (
    var.mcp_scratchpad_image != "" 
    ? var.mcp_scratchpad_image 
    : "${azurerm_container_registry.main.login_server}/mcp-scratchpad:latest"
  )
  
  agent_location_scout_image = (
    var.agent_location_scout_image != "" 
    ? var.agent_location_scout_image 
    : "${azurerm_container_registry.main.login_server}/agent-location-scout:latest"
  )
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}
