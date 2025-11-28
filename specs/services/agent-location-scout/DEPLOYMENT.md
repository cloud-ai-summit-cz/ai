# Service Deployment: agent-location-scout

Deployment procedures for the LangGraph-based Foundry Hosted Agent.

## Pipelines

### CI Stages
1. **Lint**: `ruff check`, `ruff format --check`
2. **Type Check**: `pyright`
3. **Unit Tests**: `pytest tests/unit`
4. **Local Test**: Run with `from_langgraph(agent).run()`, test via REST
5. **Container Build**: Docker build and scan

### CD Stages
1. **Build**: Docker image build
2. **Push**: Push to Azure Container Registry
3. **Deploy**: Create/update Foundry Hosted Agent version
4. **Start**: Start agent deployment
5. **Verify**: Test via Foundry Responses API

## Environments

| Environment | Branch/Artifact | Purpose | Approvals |
|-------------|-----------------|---------|-----------|
| Local | feature/* | Development | None |
| Dev | main | Integration testing | Auto |
| Production | release/* | Live demo | Manual |

## Release Steps

### Preconditions
- [ ] All CI checks pass
- [ ] Local testing with `localhost:8088` successful
- [ ] Container image scanned for vulnerabilities

### Deployment Procedure

1. **Build and push container image**:
   ```bash
   docker build -t cofilotacr.azurecr.io/agent-location-scout:v{version} .
   docker push cofilotacr.azurecr.io/agent-location-scout:v{version}
   ```

2. **Deploy to Foundry**:
   ```python
   from azure.ai.projects import AIProjectClient
   from azure.ai.projects.models import ImageBasedHostedAgentDefinition, ProtocolVersionRecord, AgentProtocol
   from azure.identity import DefaultAzureCredential

   client = AIProjectClient(
       endpoint=PROJECT_ENDPOINT,
       credential=DefaultAzureCredential()
   )

   agent = client.agents.create_version(
       agent_name="location-scout",
       definition=ImageBasedHostedAgentDefinition(
           container_protocol_versions=[
               ProtocolVersionRecord(protocol=AgentProtocol.RESPONSES, version="v1")
           ],
           cpu="1",
           memory="2Gi",
           image="cofilotacr.azurecr.io/agent-location-scout:v{version}",
           environment_variables={
               "AZURE_AI_PROJECT_ENDPOINT": PROJECT_ENDPOINT,
               "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
               "MCP_SCRATCHPAD_URL": "http://mcp-scratchpad",
               "MCP_LOCATION_URL": "http://mcp-location"
           }
       )
   )
   ```

3. **Start the agent**:
   ```bash
   az cognitiveservices agent start \
     --account-name cofilot-foundry \
     --project-name cofilot-project \
     --name location-scout \
     --agent-version {version}
   ```

4. **Verify**:
   ```python
   # Test via Responses API
   response = openai_client.responses.create(
       input=[{"role": "user", "content": "Analyze Vienna locations"}],
       extra_body={"agent": {"name": "location-scout", "type": "agent_reference"}}
   )
   ```

### Verification & Rollback

**Rollback procedure**:
```bash
# Stop current version
az cognitiveservices agent stop \
  --account-name cofilot-foundry \
  --project-name cofilot-project \
  --name location-scout \
  --agent-version {current}

# Start previous version
az cognitiveservices agent start \
  --account-name cofilot-foundry \
  --project-name cofilot-project \
  --name location-scout \
  --agent-version {previous}
```

## Infrastructure

### Foundry Hosted Agent Configuration

```yaml
agent:
  name: location-scout
  type: hosted
  framework: langgraph
  image: cofilotacr.azurecr.io/agent-location-scout:latest
  resources:
    cpu: "1"
    memory: "2Gi"
  scaling:
    min_replicas: 1
    max_replicas: 2
  environment:
    AZURE_AI_PROJECT_ENDPOINT: ${PROJECT_ENDPOINT}
    AZURE_OPENAI_DEPLOYMENT_NAME: gpt-4o
    MCP_SCRATCHPAD_URL: http://mcp-scratchpad
    MCP_LOCATION_URL: http://mcp-location
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

# Expose hosting adapter port
EXPOSE 8088

CMD ["uv", "run", "python", "-m", "agent_location_scout"]
```

### Required Azure Resources
- Azure AI Foundry Project (North Central US)
- Azure Container Registry
- Managed Identity with ACR pull permissions
- MCP server network connectivity
- **Capability Hosts** (required for hosted agents - see below)

### Capability Hosts Setup (Critical!)

> **Important**: Hosted agents require Capability Hosts to be configured at BOTH account and project levels before agents can be started. Without this, start commands fail with "Capability Host not found" error.

**Account-level capability host**:
```bash
az rest --method PUT \
  --uri "https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.CognitiveServices/accounts/{accountName}/capabilityHosts/default?api-version=2025-06-01" \
  --headers "Content-Type=application/json" \
  --body '{"properties": {"capabilityHostKind": "Agents"}}'
```

**Project-level capability host**:
```bash
az rest --method PUT \
  --uri "https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.CognitiveServices/accounts/{accountName}/projects/{projectName}/capabilityHosts/default?api-version=2025-06-01" \
  --headers "Content-Type=application/json" \
  --body '{"properties": {"capabilityHostKind": "Agents"}}'
```

Wait for both to reach `provisioningState: Succeeded` before starting agents.

### IaC Reference
- Terraform: `infra/services/agent-location-scout.tf`

## REST API Reference (Data Plane)

> **Note**: The `az cognitiveservices agent start/stop` CLI commands may not be available in all CLI versions. Use the data plane REST API directly:

### Start Agent Container
```bash
# Get access token for AI Foundry
TOKEN=$(az account get-access-token --resource "https://ai.azure.com" --query accessToken -o tsv)

# Start the agent container
curl -X POST \
  "https://{account}.services.ai.azure.com/api/projects/{project}/agents/{agentName}/versions/{version}/containers/default:start?api-version=2025-11-15-preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{}"
```

### Stop Agent Container
```bash
curl -X POST \
  "https://{account}.services.ai.azure.com/api/projects/{project}/agents/{agentName}/versions/{version}/containers/default:stop?api-version=2025-11-15-preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{}"
```

### Update Agent (replicas)
```bash
curl -X POST \
  "https://{account}.services.ai.azure.com/api/projects/{project}/agents/{agentName}/versions/{version}/containers/default:update?api-version=2025-11-15-preview" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"min_replicas": 1, "max_replicas": 2}'
```

### Get Agent Version Status
```bash
curl -s \
  "https://{account}.services.ai.azure.com/api/projects/{project}/agents/{agentName}/versions/{version}?api-version=2025-11-15-preview" \
  -H "Authorization: Bearer $TOKEN"
```

**Response includes**:
- `hosted_agent_definition.container.status`: `Starting`, `Running`, `Stopping`, `Stopped`, `Failed`

## Limitations (Preview)

- **Region**: North Central US only
- **Max replicas**: 5 (preview limit)
- **Billing**: Free during preview, expected Feb 2026
- **CLI**: `az cognitiveservices agent` commands may not be available - use REST API
