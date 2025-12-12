# Workflow Agent Provisioning

Provisions the invoice workflow agents to Azure AI Foundry in sequence.

Agents provisioned (from `src/workflows/invoice-processing-seq/setup_agents.sh`):
- invoice-intake
- invoice-validation
- invoice-validation-summary
- invoice-summary
- invoice-mailer

## Usage

```bash
cd deploy_workflow/agent_provisioning

# Provision all agents (create)
uv run python provision_all.py

# List configured agents
uv run python provision_all.py --list

# Provision one agent
uv run python provision_all.py --agent invoice-validation

# Destroy all agents (calls each agent's provision.py destroy)
uv run python provision_all.py --action destroy

# Override agent `.env` / environment variables via CLI flags
uv run python provision_all.py \
  --azure-ai-foundry-endpoint "https://<foundry-project>.services.ai.azure.com/api/projects/proj-default" \
  --model-deployment-name "gpt-5" \
  --mcp-invoice-data-url "https://<example>.<region>.azurecontainerapps.io/mcp" \
  --action create
```

## Configuration

Edit `config.yaml` to add/remove agents or change provisioning commands.

Each entry is:

```yaml
agents:
  - name: invoice-intake
    path: agent-invoice-intake
    command: uv run python provision.py create
```

### Environment Overrides

You can provide defaults in `config.yaml` and/or override them per agent.

Precedence (lowest → highest):
- `settings.env_overrides` (global defaults)
- `agents[].overrides` (per-agent overrides)
- `provision_all.py` CLI flags

`provision_all.py` reads each agent's `.env.example` and only passes the flags that agent supports.
This avoids breaking agents that don't use MCP settings, etc.

Example `config.yaml`:

```yaml
settings:
  src_dir: "../../src"
  env_overrides:
    AZURE_AI_FOUNDRY_ENDPOINT: "https://<foundry-project>.services.ai.azure.com/api/projects/proj-default"
    MODEL_DEPLOYMENT_NAME: "gpt-5"
    MCP_INVOICE_DATA_URL: "https://<example>.<region>.azurecontainerapps.io/mcp"
    APPLICATIONINSIGHTS_CONNECTION_STRING: "InstrumentationKey=...;IngestionEndpoint=..."

agents:
  - name: invoice-validation
    path: agent-invoice-validation
    command: uv run python provision.py create
    overrides:
      MODEL_DEPLOYMENT_NAME: "gpt-5"
```

## Prerequisites

- Azure credentials configured (e.g. `az login`)
- Each agent folder under `src/` has:
  - `provision.py` provisioning script
  - `.env` (or environment variables) with required settings (Foundry endpoint, model deployment name, and any MCP URLs)

Tip: ensure your workflow deployment outputs (Foundry project endpoint + MCP server URL) are copied into the agent `.env` files before provisioning.

If you use `settings.env_overrides` or CLI flags, you don't need to update each agent's `.env` locally.
