# Agent Provisioning

Provisions all agents to Azure AI Foundry in sequence.

## Usage

```bash
# Provision all agents
uv run python provision_all.py

# List configured agents
uv run python provision_all.py --list

# Provision a specific agent
uv run python provision_all.py --agent market-analyst
```

## Configuration

Edit `config.yaml` to add/remove agents or change provisioning commands.

```yaml
agents:
  - name: my-agent
    path: agent-my-agent           # Folder name under src/
    command: uv run python provision_foundry_agent_base.py create
```

## Prerequisites

- Azure credentials configured (logged in via `az login`)
- Each agent folder must have:
  - `provision_foundry_agent_base.py` - provisioning script
  - `.env` file with `AZURE_AI_FOUNDRY_ENDPOINT`
