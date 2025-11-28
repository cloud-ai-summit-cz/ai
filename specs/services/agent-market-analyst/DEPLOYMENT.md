# Service Deployment: agent-market-analyst

Deployment for Foundry Native agent.

## Pipelines

### CD Stages
1. **Provision**: Run provisioning script
2. **Verify**: Test agent via SDK

## Deployment Procedure

Agent is provisioned via Python script:

```bash
# From agents directory
uv run python -m agents.provision create
```

The script:
1. Deletes existing agent if present (idempotent)
2. Creates agent with prompt and MCP tool definitions
3. Registers MCP server connections

## Infrastructure

### Agent Configuration
- **Model**: gpt-4o (Foundry deployment)
- **MCP Servers**: mcp-scratchpad, mcp-market-data
- **Hosting**: AI Foundry Managed

### Required Azure Resources
- Azure AI Foundry Project
- MCP server connections configured in Foundry

### IaC Reference
- Terraform: `infra/foundry/agents.tf` (agent provisioning)
- Python: `agents/agents/provision.py`
