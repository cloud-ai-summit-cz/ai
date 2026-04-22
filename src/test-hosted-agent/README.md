# Test Hosted Agent

Minimal LangGraph agent for testing Azure AI Foundry hosted agent functionality.
Based on official Azure SDK samples.

## Purpose

This is a **minimal test agent** to isolate RBAC/authentication issues when deploying to Azure AI Foundry as a hosted agent. It uses the simplest possible patterns from the official SDK samples.

## Files

| File | Description |
|------|-------------|
| `main.py` | Simple ReAct agent using `AzureChatOpenAI` (official simple_react_agent pattern) |
| `main_with_managed_identity.py` | Calculator agent with explicit managed identity auth (agent_calculator pattern) |
| `requirements.txt` | Minimal dependencies for container |
| `Dockerfile` | Container build file |

## Environment Variables

The hosted agent platform injects these automatically:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Cognitive services endpoint |
| `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME` | Model deployment name |
| `OPENAI_API_VERSION` | API version |

## Local Testing

```bash
# Create .env from template
cp .env-template .env
# Edit .env with your values

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Build & Deploy

```bash
# Build container
docker build -t test-hosted-agent:latest .

# Push to ACR
docker tag test-hosted-agent:latest <acr>.azurecr.io/test-hosted-agent:latest
docker push <acr>.azurecr.io/test-hosted-agent:latest
```

## References

- [azure-ai-agentserver-langgraph samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/agentserver/azure-ai-agentserver-langgraph/samples)
- [simple_react_agent](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/agentserver/azure-ai-agentserver-langgraph/samples/simple_react_agent)
- [agent_calculator](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/agentserver/azure-ai-agentserver-langgraph/samples/agent_calculator)
