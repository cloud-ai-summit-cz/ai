# Shared Observability Strategy

Telemetry standards for Cofilot AI Platform. Focus on demo visibility and debugging.

---

## Infrastructure Overview

All observability infrastructure is managed via Terraform in `deploy/azure/terraform/`:

| Resource | Purpose | Terraform File |
|----------|---------|----------------|
| Log Analytics Workspace | Centralized log storage | `capp.env.tf` |
| Application Insights | Tracing and telemetry | `observability.tf` |
| Diagnostic Settings | Foundry metrics/logs | `observability.tf` |

### Getting Connection Strings

After running `terraform apply`, retrieve observability configuration:

```bash
cd deploy/azure/terraform

# Application Insights connection string (for all agents)
terraform output -raw application_insights_connection_string

# Log Analytics workspace ID (for Kusto queries)
terraform output log_analytics_workspace_id
```

---

## Application Insights Integration

All agents MUST send traces to Application Insights for unified observability.

### Required Environment Variable

Every agent must have this environment variable set:

```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=<key>;IngestionEndpoint=https://northcentralus-0.in.applicationinsights.azure.com/
```

Get the value from Terraform: `terraform output -raw application_insights_connection_string`

### Python Setup with OpenTelemetry

```python
# app/telemetry.py
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def configure_telemetry(service_name: str):
    """Configure OpenTelemetry with Azure Monitor export."""
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if connection_string:
        configure_azure_monitor(
            connection_string=connection_string,
            service_name=service_name,
        )
        
        # Auto-instrument FastAPI and HTTP clients
        FastAPIInstrumentor.instrument()
        HTTPXClientInstrumentor().instrument()
        
        print(f"Telemetry configured for {service_name}")
    else:
        print("Warning: APPLICATIONINSIGHTS_CONNECTION_STRING not set, tracing disabled")

# Get tracer for manual instrumentation
tracer = trace.get_tracer(__name__)
```

### Agent Initialization Pattern

```python
# main.py
from app.telemetry import configure_telemetry

# Configure telemetry FIRST before importing other modules
configure_telemetry(service_name="agent-location-scout")

from fastapi import FastAPI
from app.routes import router

app = FastAPI()
app.include_router(router)
```

### Required Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    "azure-monitor-opentelemetry>=1.6.0",
    "opentelemetry-instrumentation-fastapi>=0.45b0",
    "opentelemetry-instrumentation-httpx>=0.45b0",
]
```

---

## Instrumentation Baseline

### Preferred Libraries

| Language | Logging | Metrics | Tracing |
|----------|---------|---------|---------|
| Python | structlog | prometheus-client (optional) | OpenTelemetry + Azure Monitor |
| JavaScript | pino | N/A | N/A |

### Correlation & Context

Every request/operation should carry:

| Field | Description | Example |
|-------|-------------|---------|
| `request_id` | Unique request identifier | `req_abc123` |
| `session_id` | Research/workflow session | `sess_xyz789` |
| `workflow_id` | Invoice workflow ID | `wf_inv456` |
| `agent` | Current agent name | `market-analyst` |
| `trace_id` | OpenTelemetry trace ID | `4bf92f3577b34da6a3ce929d0e0e4736` |

### Propagation Format

W3C Trace Context headers:
- `traceparent`
- `tracestate`

---

## Logging

### Log Format (JSON)

```json
{
  "timestamp": "2025-12-01T10:05:00.123Z",
  "level": "info",
  "message": "Tool call completed",
  "request_id": "req_abc123",
  "session_id": "sess_xyz789",
  "agent": "market-analyst",
  "tool": "get_market_overview",
  "duration_ms": 234,
  "status": "success"
}
```

### Python Logging Setup

```python
# app/logging_config.py
import structlog
import logging

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
from structlog import get_logger
logger = get_logger()

async def handle_request(request_id: str, session_id: str):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        session_id=session_id
    )
    
    logger.info("Processing started")
    # ... all subsequent logs include request_id and session_id
```

### Log Levels in Production

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Disabled in production | Detailed tool responses |
| INFO | Normal operations | Agent started, tool completed |
| WARNING | Recoverable issues | Retry triggered, timeout recovered |
| ERROR | Failures requiring attention | Tool failed, agent error |
| CRITICAL | System-wide issues | Service unavailable |

### PII/Sensitive Data Masking

```python
# Never log these directly
SENSITIVE_FIELDS = ['api_key', 'token', 'password', 'key']

def mask_sensitive(data: dict) -> dict:
    """Mask sensitive fields before logging."""
    return {
        k: '***MASKED***' if any(s in k.lower() for s in SENSITIVE_FIELDS) else v
        for k, v in data.items()
    }

# Usage
logger.info("Config loaded", config=mask_sensitive(config_dict))
```

---

## Metrics & SLOs

### Key Metrics

| Metric | Definition | Target/SLO | Collection |
|--------|------------|------------|------------|
| `research_session_duration_seconds` | Time from query to report | < 180s (3 min) | Histogram |
| `invoice_workflow_duration_seconds` | Time from upload to notification | < 10s | Histogram |
| `agent_turn_duration_seconds` | Single agent turn time | < 5s | Histogram |
| `tool_call_duration_seconds` | MCP tool call latency | < 2s | Histogram |
| `sse_event_latency_ms` | Time from event to UI | < 500ms | Histogram |
| `agent_error_rate` | Errors per agent invocation | < 5% | Counter |
| `tool_call_error_rate` | Tool failures | < 1% | Counter |

### Demo-Specific Metrics

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| `demo_session_success` | Did demo complete successfully | N/A (dashboard) |
| `checklist_completion_rate` | % checklist items completed | < 100% = investigate |
| `user_question_response_time` | Time waiting for user input | > 60s = timeout |

### Prometheus Metrics (Optional)

```python
# app/metrics.py
from prometheus_client import Histogram, Counter

AGENT_DURATION = Histogram(
    'agent_turn_duration_seconds',
    'Duration of agent turn',
    ['agent', 'scenario']
)

TOOL_CALLS = Counter(
    'tool_calls_total',
    'Total tool calls',
    ['tool', 'mcp_server', 'status']
)

# Usage
with AGENT_DURATION.labels(agent='market-analyst', scenario='research').time():
    result = await invoke_agent(...)

TOOL_CALLS.labels(
    tool='get_market_overview',
    mcp_server='mcp-market-data',
    status='success'
).inc()
```

---

## Tracing

### Azure Application Insights Integration

All agents export traces to Azure Application Insights via OpenTelemetry. The integration is configured automatically when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set.

See the **Application Insights Integration** section above for setup instructions.

### Manual Span Creation

```python
# For custom spans beyond auto-instrumentation
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("invoke_agent")
async def invoke_agent(agent_name: str, message: str):
    span = trace.get_current_span()
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("message.length", len(message))
    # ...
```

---

## Real-Time UI Events (ADR-007)

The Research Orchestrator provides real-time visibility into subagent activity via direct events streamed to the frontend over SSE.

> **See**: `specs/platform/decisions/ADR-007-direct-orchestrator-events-for-ui.md` for the current architecture decision.
>
> **Historical Note**: ADR-005 originally proposed using trace polling for UI events, but this was superseded due to 2-5 second App Insights ingestion latency. See ADR-007 for details.

### Architecture

```
┌─────────────┐      SSE        ┌───────────────────────┐
│   Frontend  │ ◄─────────────  │ Research Orchestrator │
│   (React)   │  Direct Events  │     (Backend API)     │
└─────────────┘                 └───────────────────────┘
                                         │
                                         │ Middleware intercepts
                                         │ agent/tool calls
                                         ▼
                               ┌─────────────────────────┐
                               │    Event Middleware     │
                               │  (emit_agent_event())   │
                               └─────────────────────────┘
                                         │
                               ┌─────────┼─────────┐
                               │         │         │
                       ┌───────▼──┐ ┌────▼────┐ ┌──▼──────┐
                       │ market-  │ │location-│ │ mcp-    │
                       │ analyst  │ │ scout   │ │scratchpad│
                       └──────────┘ └─────────┘ └─────────┘
```

### SSE Event Types for UI

| Event Type | Payload | When Emitted |
|------------|---------|--------------|
| `tool_call_started` | `{tool, mcp_server, agent, timestamp}` | Tool invocation begins |
| `tool_call_completed` | `{tool, mcp_server, agent, duration_ms, success}` | Tool invocation ends |
| `agent_started` | `{agent, timestamp}` | Agent invocation begins |
| `agent_completed` | `{agent, duration_ms, success}` | Agent invocation ends |
| `scratchpad_updated` | `{section, content_preview}` | Scratchpad content changes |
| `synthesis_completed` | `{report_length}` | Final report ready |
| `heartbeat` | `{timestamp}` | Connection keep-alive (every 15s) |

### Latency Expectations

| Stage | Expected Latency |
|-------|------------------|
| Event emitted by middleware | Immediate |
| SSE delivery to frontend | < 100ms |
| **Total end-to-end** | **< 100ms** |

---

## Observability-Only Trace Polling (ADR-005)

While UI events are now delivered directly, the original trace polling infrastructure remains available for backend observability, debugging, and dashboard queries.

> **Note**: This is **not** used for real-time UI updates. It's for post-hoc analysis and dashboards.

### Session Correlation via operation_Id

All traces within a research session share the same `operation_Id` (W3C trace ID):

```python
# At session start, orchestrator creates trace context
from opentelemetry import trace

tracer = trace.get_tracer("research-orchestrator")
with tracer.start_as_current_span("research_session") as span:
    span.set_attribute("session.id", session_id)
    span.set_attribute("research.query", user_query)
    # All subagent calls inherit this operation_Id
```

### KQL Queries for Trace Analysis

```kusto
// All traces for a research session
union traces, dependencies, requests
| where operation_Id == "your-session-trace-id"
| order by timestamp asc

// Tool calls by agent
dependencies
| where customDimensions.agent_name != ""
| summarize count(), avg(duration) by 
    tostring(customDimensions.agent_name),
    name
| order by count_ desc

// Session timeline
union traces, dependencies
| where operation_Id == "your-session-trace-id"
| project timestamp, name, duration, customDimensions
| order by timestamp asc
| render timechart
```

---

### Viewing Traces in Azure Portal

1. Go to Azure Portal → Application Insights → your instance
2. Navigate to **Transaction search** for individual traces
3. Use **Application map** to see service dependencies
4. Use **Performance** to analyze latency distributions

### Kusto Queries for Traces

```kusto
// All traces for a session
traces
| where customDimensions.session_id == "sess_abc123"
| order by timestamp

// Agent invocation latency
requests
| where name contains "invoke_agent"
| summarize avg(duration), percentile(duration, 95) by bin(timestamp, 5m)

// Failed tool calls
exceptions
| where customDimensions.tool_name != ""
| summarize count() by customDimensions.tool_name, bin(timestamp, 1h)
```

### Sampling Strategy

| Environment | Strategy | Rate |
|-------------|----------|------|
| Local | Always sample | 100% |
| Dev | Always sample | 100% |
| Demo | Always sample | 100% |

> For production, would use tail-based sampling to capture errors and slow requests.

### Span Naming Conventions

| Span Name | When Created | Key Attributes |
|-----------|--------------|----------------|
| `POST /research/start` | API endpoint | `session_id` |
| `invoke_agent` | Agent invocation | `agent.name`, `thread_id` |
| `tool_call` | MCP tool call | `tool.name`, `mcp_server` |
| `cosmos_operation` | DB operation | `operation`, `container` |

---

## Real-Time Event Streaming

### SSE Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │◄────│  Backend API │◄────│   Agent/MCP  │
│     (Vue)    │ SSE │   (FastAPI)  │Event│   Activity   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### SSE Endpoint

```python
# app/routes/sse.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.event_bus import EventBus

router = APIRouter()
event_bus = EventBus()

@router.get("/events/{session_id}")
async def stream_events(session_id: str):
    async def event_generator():
        async for event in event_bus.subscribe(session_id):
            yield f"event: {event['type']}\n"
            yield f"data: {json.dumps(event['data'])}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### Event Bus Implementation

```python
# app/services/event_bus.py
import asyncio
from collections import defaultdict
from typing import AsyncIterator

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
    
    async def publish(self, session_id: str, event: dict):
        """Publish event to all subscribers of a session."""
        for queue in self._subscribers[session_id]:
            await queue.put(event)
    
    async def subscribe(self, session_id: str) -> AsyncIterator[dict]:
        """Subscribe to events for a session."""
        queue = asyncio.Queue()
        self._subscribers[session_id].append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers[session_id].remove(queue)

# Global instance
event_bus = EventBus()
```

### Frontend SSE Client

```typescript
// src/composables/useEventStream.ts
export function useEventStream(sessionId: string) {
  const events = ref<AgentEvent[]>([])
  const status = ref<'connecting' | 'connected' | 'error'>('connecting')
  
  const connect = () => {
    const eventSource = new EventSource(`/api/events/${sessionId}`)
    
    eventSource.onopen = () => {
      status.value = 'connected'
    }
    
    eventSource.addEventListener('agent_activity', (e) => {
      const data = JSON.parse(e.data)
      events.value.push(data)
    })
    
    eventSource.addEventListener('scratchpad_updated', (e) => {
      // Update scratchpad view
    })
    
    eventSource.onerror = () => {
      status.value = 'error'
      // Reconnect after delay
      setTimeout(connect, 3000)
    }
    
    return eventSource
  }
  
  onMounted(() => connect())
  
  return { events, status }
}
```

---

## Alerting & Dashboards

### Demo Dashboard Components

| Panel | Visualization | Data Source |
|-------|---------------|-------------|
| Active Sessions | Counter | Cosmos DB query |
| Agent Activity Timeline | Timeline/Gantt | SSE events |
| Scratchpad Sections | Card grid | Cosmos DB |
| Checklist Progress | Progress bar | Session data |
| Workflow Events | Event list | Workflow events |
| Error Rate | Gauge | Metrics/Logs |

### Dashboard Layout (Research UI)

```
┌─────────────────────────────────────────────────────────────────┐
│  Query: "Should Cofilot expand to Vienna?"         [In Progress]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐│
│  │   Agent Activity        │  │   Shared Scratchpad            ││
│  │   ─────────────────     │  │   ──────────────────           ││
│  │   🔵 market-analyst     │  │   📊 Market Findings [✓]       ││
│  │      get_market_overview│  │   🏢 Competitor Analysis [✓]   ││
│  │      → Vienna: €450M    │  │   📍 Locations [ ]             ││
│  │   🟢 competitor-analyst │  │   📜 Regulations [ ]           ││
│  │      list_competitors   │  │   💰 Financial [ ]             ││
│  │      → 5 competitors    │  │   ❓ User Answers [1 pending]  ││
│  │   ⏳ location-scout     │  │                                ││
│  │      [running...]       │  │                                ││
│  └─────────────────────────┘  └────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │   Checklist                                    [4/8 complete]││
│  │   ☑ Market size documented    ☑ Competitors profiled        ││
│  │   ☑ Customer segments         ☐ Positioning gaps            ││
│  │   ☐ Locations evaluated       ☐ Regulations listed          ││
│  │   ☐ Financial projection      ☐ Final recommendation        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │   ❓ Pending Question                                        ││
│  │   "What is your target budget for initial investment?"       ││
│  │   [€100k-150k] [€150k-200k] [€200k-300k] [Custom...]        ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard Layout (Invoice UI)

```
┌─────────────────────────────────────────────────────────────────┐
│  Invoice: INV-2025-0042                           [Processing]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐│
│  │   Workflow Progress     │  │   Invoice Details              ││
│  │   ─────────────────     │  │   ──────────────────           ││
│  │   ✅ Intake             │  │   Vendor: Coffee Beans Co.     ││
│  │   ✅ Validation         │  │   PO#: PO-12345                ││
│  │   ✅ Reconciliation     │  │   Amount: €1,020.00            ││
│  │   🔵 Routing            │  │   Date: 2025-11-25             ││
│  │   ⏳ Recommendation     │  │   Tax: €170.00 (20%)           ││
│  │   ⏳ Notification       │  │                                ││
│  └─────────────────────────┘  └────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │   Event Stream                                               ││
│  │   ────────────                                               ││
│  │   14:00:01 📥 Invoice received                               ││
│  │   14:00:02 🔍 Data extracted (12 fields, 94% confidence)     ││
│  │   14:00:04 ✅ PO validated - exists and active               ││
│  │   14:00:05 ✅ Policy checks passed (2/2)                     ││
│  │   14:00:06 ✅ Reconciliation complete - exact match          ││
│  │   14:00:07 👤 Routing to Jan Novak (jan.novak@cofilot.cz)   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Alert Rules (Optional)

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Demo Session Stuck | No events for 60s | Warning | Show warning in UI |
| Agent Error | Error count > 3 | Warning | Log for review |
| Service Unavailable | Health check fails | Critical | Notify presenter |

---

## Log Aggregation

### Local Development

```yaml
# docker-compose.yml - logs go to stdout
services:
  backend-api:
    # ...
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Azure (Container Apps + Application Insights)

Container Apps automatically:
- Collect stdout/stderr logs
- Send to Azure Monitor / Log Analytics
- Provide log streaming in Azure Portal

Application Insights provides:
- Distributed tracing across all agents
- Dependency tracking (OpenAI calls, HTTP requests)
- Exception and failure analysis
- Performance metrics and dashboards

#### Query Container Logs via Log Analytics

```kusto
// All logs for a session
ContainerAppConsoleLogs_CL
| where Log_s contains "sess_abc123"
| order by TimeGenerated

// Agent errors
ContainerAppConsoleLogs_CL
| where Log_s contains "ERROR"
| where Log_s contains "agent"
| summarize count() by bin(TimeGenerated, 5m)
```

#### Query Traces via Application Insights

```kusto
// All requests for an agent
requests
| where cloud_RoleName == "agent-location-scout"
| summarize count(), avg(duration) by name
| order by count_ desc

// Dependency calls (OpenAI, HTTP)
dependencies
| where cloud_RoleName contains "agent"
| summarize count(), avg(duration) by target, name
| order by avg_duration desc

// Exceptions by agent
exceptions
| summarize count() by cloud_RoleName, type
| order by count_ desc
```

---

## Specification by Example

| Scenario | Given | When | Then |
|----------|-------|------|------|
| End-to-end trace | Request starts research | All agents complete | Single trace ID across all spans |
| SSE delivery | Agent completes tool call | Event published | UI receives event < 500ms |
| Log correlation | Error occurs in MCP server | Logs queried | request_id links to original API call |
| Metric collection | 10 research sessions run | Metrics queried | Duration histogram shows distribution |
| Dashboard update | Checklist item completed | Cosmos DB updated | Dashboard reflects change < 1s |

---

## Service Health Checks

### FastAPI Health Endpoint

```python
# app/routes/health.py
from fastapi import APIRouter, Response
from app.services.cosmos_client import cosmos_client

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}

@router.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies dependencies."""
    checks = {}
    
    # Check Cosmos DB
    try:
        await cosmos_client.read_database()
        checks["cosmos"] = "ok"
    except Exception as e:
        checks["cosmos"] = f"error: {str(e)}"
    
    # Check AI Foundry (optional)
    # ...
    
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    
    return Response(
        content=json.dumps({"checks": checks}),
        status_code=status_code,
        media_type="application/json"
    )
```

### Container Apps Health Probes

```hcl
# Terraform - Container App health configuration
resource "azapi_resource" "backend_api" {
  body = jsonencode({
    properties = {
      template = {
        containers = [{
          probes = [
            {
              type = "liveness"
              httpGet = {
                path = "/health"
                port = 8000
              }
              periodSeconds = 10
            },
            {
              type = "readiness"
              httpGet = {
                path = "/health/ready"
                port = 8000
              }
              periodSeconds = 5
            }
          ]
        }]
      }
    }
  })
}
```
