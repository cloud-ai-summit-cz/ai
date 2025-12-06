# Invoice Processing Workflow Backend

FastAPI backend for running agentic invoice processing workflows with SSE streaming.

## Setup

```bash
cd src/workflows/backend
uv sync
```

## Running

```bash
uv run python main.py
# Or with hot reload:
uv run uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/workflow/run` | POST | Run workflow with invoice image (multipart form) |
| `/workflow/run/json` | POST | Run workflow without image (JSON body) |

## Containerization & Azure Container Apps

Build and run locally:

```bash
docker build -t <acr-name>.azurecr.io/invoice-workflow-backend:latest .
docker run --rm -p 8000:8000 \
  -e AZURE_AI_ENDPOINT="https://ai-foundry-<region>.services.ai.azure.com/api/projects/<project-name>" \
  <acr-name>.azurecr.io/invoice-workflow-backend:latest
```

Push to Azure Container Registry (ACR):

```bash
az acr login --name <acr-name>
docker push <acr-name>.azurecr.io/invoice-workflow-backend:latest
```

Update Container App (existing app name: `be-invoice-demo`):

```bash
az containerapp update \
  --name be-invoice-demo \
  --resource-group <rg-name> \
  --image <acr-name>.azurecr.io/invoice-workflow-backend:latest \
  --set-env-vars AZURE_AI_ENDPOINT="https://ai-foundry-<region>.services.ai.azure.com/api/projects/<project-name>"
```

Identity & permissions:

- Ensure the Container App has a managed identity (`az containerapp identity assign --name be-invoice-demo --resource-group <rg-name> --system`).
- Grant that identity access to the Azure AI Project (e.g., `Azure AI Developer` or equivalent role).

## Example Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Run Workflow with Invoice

```bash
curl -X POST http://localhost:8000/workflow/run \
  -F "message=Please extract the data from this invoice." \
  -F "invoice=@path/to/invoice.jpg"
```

### Run Workflow (JSON)

```bash
curl -X POST http://localhost:8000/workflow/run/json \
  -H "Content-Type: application/json" \
  -d '{"message": "Process this request", "workflow_name": "wf1", "workflow_version": "1"}'
```

## Event Types

The SSE stream emits `WorkflowEvent` objects with these types:

- `workflow_started` / `workflow_completed` / `workflow_failed`
- `response_created` / `response_in_progress` / `response_completed`
- `actor_started` / `actor_completed`
- `text_delta` / `text_done` / `message_completed`
- `mcp_tools_listed` / `mcp_call_in_progress` / `mcp_call_completed`
- `error`
