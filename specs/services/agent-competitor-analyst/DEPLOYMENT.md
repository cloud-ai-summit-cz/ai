# Service Deployment: agent-competitor-analyst

Deployment for Foundry Native agent.

## Deployment Procedure

Agent is provisioned via Python script:

```bash
uv run python -m agents.provision create
```

### Agent Configuration
- **Model**: gpt-4o
- **MCP Servers**: mcp-scratchpad, mcp-competitor
- **Hosting**: AI Foundry Managed
