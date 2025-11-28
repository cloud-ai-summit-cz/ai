locals {
  # Resource naming prefix
  name_prefix = "mcp-scratchpad"

  # Common tags applied to all resources
  common_tags = {
    Project   = "mcp-scratchpad"
    ManagedBy = "terraform"
  }
}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}
