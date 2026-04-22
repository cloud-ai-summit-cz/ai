# Service Deployment: agent-synthesizer

Deployment for Foundry Native agent.

## Deployment Procedure

Agent is provisioned via Python script:

```bash
uv run python -m agents.provision create
```

### Agent Configuration
- **Model**: gpt-4o (needs longer context for synthesis)
- **MCP Servers**: mcp-scratchpad
- **Hosting**: AI Foundry Managed
