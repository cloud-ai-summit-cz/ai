# Shared Deployment Strategy

Deployment workflow and infrastructure for Cofilot AI Platform.

## Environments

| Environment | Purpose | Source Branch / Tag | Promotion Criteria |
|-------------|---------|---------------------|-------------------|
| `local` | Developer workstation | Any branch | N/A |
| `dev` | Integration testing | `main` | PR merged |
| `demo` | Conference/presentation | `release/*` tag | Manual approval |

> **Note**: This is a demo project. No staging/production environments needed.

---

## Infrastructure Overview

### Azure Resources (Terraform + Python)

| Resource | Provisioning | Notes |
|----------|--------------|-------|
| Resource Group | Terraform | Single RG for all resources |
| Azure AI Foundry Project | Terraform (azapi) | Hub + Project |
| Azure OpenAI | Terraform | Model deployments |
| Azure AI Search | Terraform | Semantic search indexes |
| Azure Cosmos DB | Terraform | Serverless, single database |
| Azure Container Apps Environment | Terraform | Consumption plan |
| Azure Container Registry | Terraform | Basic tier |
| Azure Container Apps | Terraform | All containers (6 agents + 7 MCP servers) |
| **AI Foundry Agents** | **Python** | Provisioned via SDK |

### Why Python for Agents?

AI Foundry Agent definitions (prompts, tools, model config) are better managed as code:
- Agent prompts iterate frequently during development
- Tool connections require SDK operations
- Thread management needs programmatic control
- Easier to version control and test

---

## Service Inventory

### Agents (6 total)

| Agent | Type | Framework | Description |
|-------|------|-----------|-------------|
| `agent-research-orchestrator` | MAF Agent | Microsoft Agent Framework | Coordinates research workflow |
| `agent-market-analyst` | Foundry Native | Azure AI Foundry | Market research and analysis |
| `agent-competitor-analyst` | Foundry Native | Azure AI Foundry | Competitive landscape analysis |
| `agent-location-scout` | LangGraph | LangGraph + Azure | Location evaluation |
| `agent-finance-analyst` | LangGraph | LangGraph + Azure | Financial analysis |
| `agent-synthesizer` | Foundry Native | Azure AI Foundry | Research synthesis |

### Agent Registry

Foundry Native agents (market-analyst, competitor-analyst, synthesizer) are provisioned via Python scripts. Their IDs are automatically stored in `deploy/foundry_agents.yaml` to be consumed by the Research Orchestrator.

### MCP Servers (7 total)

| MCP Server | Port | Description |
|------------|------|-------------|
| `mcp-scratchpad` | 8010 | Persistent storage for agent notes |
| `mcp-web-search` | 8011 | Web search via Tavily/Bing |
| `mcp-business-registry` | 8012 | Czech business registry (ARES) |
| `mcp-government-data` | 8013 | Government statistics (ČSÚ) |
| `mcp-demographics` | 8014 | Demographics data |
| `mcp-real-estate` | 8015 | Real estate listings |
| `mcp-calculator` | 8016 | Financial calculations |

---

## Repository Structure

```
.
├── infra/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── versions.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── locals.tf
│   │   ├── ai_foundry.tf         # AI Foundry hub + project
│   │   ├── ai_services.tf        # OpenAI, Search, Doc Intelligence
│   │   ├── cosmos.tf             # Cosmos DB
│   │   ├── container_apps.tf     # Container Apps environment
│   │   └── containers.tf         # Individual container definitions
│   └── scripts/
│       └── deploy.ps1            # Deployment orchestration
│
├── src/
│   ├── agent-research-orchestrator/   # MAF-based orchestrator
│   ├── agent-market-analyst/          # Foundry Native agent
│   ├── agent-competitor-analyst/      # Foundry Native agent
│   ├── agent-location-scout/          # LangGraph agent
│   ├── agent-finance-analyst/         # LangGraph agent
│   ├── agent-synthesizer/             # Foundry Native agent
│   ├── mcp-scratchpad/                # Persistent notes storage
│   ├── mcp-web-search/                # Web search capability
│   ├── mcp-business-registry/         # Czech business registry
│   ├── mcp-government-data/           # Government statistics
│   ├── mcp-demographics/              # Demographics data
│   ├── mcp-real-estate/               # Real estate listings
│   └── mcp-calculator/                # Financial calculations
│
├── mock-data/
│   ├── market_vienna.json
│   ├── competitors_vienna.json
│   └── locations_vienna.json
│
├── deploy/
│   ├── local/
│   │   ├── run_all.py            # Local development runner
│   │   ├── config.yaml           # Service configuration
│   │   ├── pyproject.toml        # Runner dependencies
│   │   └── .env.example          # Environment template
│   └── azure/
│       └── deploy.ps1
│
└── specs/
    ├── platform/
    │   ├── ARCHITECTURE.md
    │   ├── DATA_MODELS.md
    │   ├── DEPLOYMENT.md
    │   └── SECURITY.md
    └── services/
        ├── agent-*/
        └── mcp-*/
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

#### `ci.yml` - Continuous Integration

```yaml
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        run: pip install uv
      
      - name: Lint Python
        run: |
          uv run ruff check .
          uv run ruff format --check .
      
      - name: Type check
        run: uv run mypy .
      
      - name: Unit tests
        run: uv run pytest tests/unit -v
      
      - name: Terraform format
        run: terraform fmt -check -recursive infra/terraform
      
      - name: Terraform validate
        run: |
          cd infra/terraform
          terraform init -backend=false
          terraform validate

  build-containers:
    runs-on: ubuntu-latest
    needs: lint-and-test
    strategy:
      matrix:
        service:
          # Agents
          - agent-research-orchestrator
          - agent-market-analyst
          - agent-competitor-analyst
          - agent-location-scout
          - agent-finance-analyst
          - agent-synthesizer
          # MCP Servers
          - mcp-scratchpad
          - mcp-web-search
          - mcp-business-registry
          - mcp-government-data
          - mcp-demographics
          - mcp-real-estate
          - mcp-calculator
    steps:
      - uses: actions/checkout@v4
      
      - name: Build container
        run: |
          docker build -t ${{ matrix.service }}:${{ github.sha }} \
            -f src/${{ matrix.service }}/Dockerfile \
            src/${{ matrix.service }}
```

#### `deploy.yml` - Deployment to Azure

```yaml
name: Deploy
on:
  push:
    tags:
      - 'release/*'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - demo

jobs:
  deploy-infrastructure:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'dev' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
      
      - name: Terraform Apply
        run: |
          cd infra/terraform
          terraform init
          terraform apply -auto-approve \
            -var="environment=${{ github.event.inputs.environment || 'dev' }}"
      
      - name: Output Terraform values
        id: tf_output
        run: |
          cd infra/terraform
          echo "acr_name=$(terraform output -raw acr_name)" >> $GITHUB_OUTPUT
          echo "foundry_endpoint=$(terraform output -raw foundry_endpoint)" >> $GITHUB_OUTPUT

  build-and-push:
    needs: deploy-infrastructure
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - agent-research-orchestrator
          - agent-market-analyst
          - agent-competitor-analyst
          - agent-location-scout
          - agent-finance-analyst
          - agent-synthesizer
          - mcp-scratchpad
          - mcp-web-search
          - mcp-business-registry
          - mcp-government-data
          - mcp-demographics
          - mcp-real-estate
          - mcp-calculator
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to ACR
        run: az acr login --name ${{ needs.deploy-infrastructure.outputs.acr_name }}
      
      - name: Build and push
        run: |
          docker build -t ${{ needs.deploy-infrastructure.outputs.acr_name }}.azurecr.io/${{ matrix.service }}:${{ github.sha }} \
            -f src/${{ matrix.service }}/Dockerfile \
            src/${{ matrix.service }}
          docker push ${{ needs.deploy-infrastructure.outputs.acr_name }}.azurecr.io/${{ matrix.service }}:${{ github.sha }}

  deploy-containers:
    needs: [deploy-infrastructure, build-and-push]
    runs-on: ubuntu-latest
    steps:
      - name: Update Container Apps
        run: |
          # Update each Container App with new image
          az containerapp update ...

  provision-foundry-agents:
    needs: deploy-containers
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Provision Foundry Native Agents
        run: |
          # Provision market-analyst
          cd src/agent-market-analyst
          uv sync
          uv run python -m market_analyst.provision create
          
          # Provision competitor-analyst
          cd ../agent-competitor-analyst
          uv sync
          uv run python -m competitor_analyst.provision create
          
          # Provision synthesizer
          cd ../agent-synthesizer
          uv sync
          uv run python -m synthesizer.provision create
```

---

## Local Development

### Prerequisites

- Python 3.11+ with uv
- Azure CLI (for Azure AI Foundry connection)
- Terraform (for infrastructure changes)

### Quick Start

```powershell
# Clone repository
git clone https://github.com/cloud-ai-summit-cz/ai.git
cd ai

# Copy environment file
cp deploy/local/.env.example deploy/local/.env
# Edit .env with your Azure credentials

# Start all services locally
cd deploy/local
uv sync
uv run python run_all.py

# Or start specific services only (edit config.yaml first)
uv run python run_all.py --config config.yaml

# Start with custom config
uv run python run_all.py --config my_custom_config.yaml
```

### Local Runner Configuration

The `deploy/local/config.yaml` controls which services to start:

```yaml
# Enable/disable individual services
agents:
  research-orchestrator: true
  market-analyst: true
  competitor-analyst: true
  location-scout: true
  finance-analyst: true
  synthesizer: true

mcp_servers:
  scratchpad: true
  web-search: true
  business-registry: true
  government-data: true
  demographics: true
  real-estate: true
  calculator: true

# Port assignments
ports:
  mcp-scratchpad: 8010
  mcp-web-search: 8011
  mcp-business-registry: 8012
  mcp-government-data: 8013
  mcp-demographics: 8014
  mcp-real-estate: 8015
  mcp-calculator: 8016
```

### Log Output

All services stream logs to a single terminal with color-coded tags:

```
[mcp-scratchpad   ] INFO:     Started server process [12345]
[mcp-web-search   ] INFO:     Uvicorn running on http://0.0.0.0:8011
[agent-market     ] Starting Market Analyst agent...
[mcp-demographics ] INFO:     Application startup complete
```

---

## Release Patterns

### Deployment Strategy

| Component | Strategy | Rationale |
|-----------|----------|-----------|
| Infrastructure | Blue/Green via Terraform | Zero-downtime infrastructure changes |
| Container Apps | Rolling update | Built-in Container Apps behavior |
| AI Foundry Agents | Recreate | Agent definitions replaced entirely |

### Rollback Procedure

```powershell
# 1. Revert to previous container images
az containerapp update --name agent-market-analyst --image $ACR.azurecr.io/agent-market-analyst:previous-sha

# 2. Revert Foundry agent definitions
cd src/agent-market-analyst
git checkout previous-release
uv run python -m market_analyst.provision create

# 3. If infrastructure change caused issue
cd infra/terraform
git checkout previous-release
terraform apply -auto-approve
```

### Time-to-Recover Targets

| Failure Type | Target Recovery | Method |
|--------------|-----------------|--------|
| Container crash | < 30 seconds | Container Apps auto-restart |
| Bad deployment | < 5 minutes | Rollback to previous image |
| Agent misconfiguration | < 10 minutes | Re-provision agents |
| Infrastructure issue | < 15 minutes | Terraform rollback |

---

## Approvals & Compliance

### PR Requirements

- [ ] All CI checks pass (lint, type-check, unit tests)
- [ ] Terraform plan reviewed (if infra changes)
- [ ] At least 1 code owner approval

### Demo Environment Deployment

- [ ] Tagged release (`release/YYYY-MM-DD`)
- [ ] Manual approval in GitHub Actions
- [ ] Smoke test after deployment

---

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Container restart | Container crashes | Container Apps detects failure | New instance starts within 30 seconds |
| Rolling deployment | New image pushed | Container App updated | Zero downtime, gradual rollout |
| Agent provisioning | Agent definitions changed | Provisioner runs | Old agents deleted, new agents created |
| Infrastructure change | Terraform modified | `terraform apply` | Resources updated without recreation where possible |
| Local development | Developer runs `run_all.py` | All enabled services start | Logs streamed with service tags |

---

## Environment Variables

### Required for All Environments

| Variable | Description | Source |
|----------|-------------|--------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint URL | Terraform output |
| `COSMOS_KEY` | Cosmos DB key (or use managed identity) | Key Vault |
| `FOUNDRY_ENDPOINT` | AI Foundry project endpoint | Terraform output |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Terraform output |
| `AI_SEARCH_ENDPOINT` | Azure AI Search endpoint | Terraform output |
| `TAVILY_API_KEY` | Tavily web search API key | Key Vault |

### Local Development Only

| Variable | Description | Default |
|----------|-------------|---------|
| `COSMOS_ENDPOINT` | Emulator endpoint | `https://localhost:8081` |
| `COSMOS_KEY` | Emulator key | Standard emulator key |
