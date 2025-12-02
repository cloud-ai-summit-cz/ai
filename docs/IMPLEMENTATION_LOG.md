# Implementation Log

Technical decisions and implementation notes for the Copilot AI Platform project.

## 2025-12-02: Subagent Tool Call Visibility Debugging

### Context
Investigating why subagent tool calls (e.g., market-analyst calling add_note) aren't appearing in the Activity panel. Also fixed SSE error event parsing issue.

### Issues Identified

1. **SSE Error Event Parsing**: When workflow fails, an `error` event with `undefined` data was causing JSON parse failures. Fixed by gracefully handling empty error data.

2. **Missing Subagent Events**: The `stream_callback` passed to `agent.as_tool()` was supposed to capture subagent tool calls, but Azure AI Foundry hosted agents execute tools **server-side** and don't stream them back via the callback. This is a known limitation documented in ADR-005.

3. **Trace Polling Gap**: Trace polling was designed to fill this gap by querying Application Insights, but the operation_Id may not be propagating correctly to hosted subagent traces.

### Changes Made

#### 1. Frontend Error Handling (`src/web-research/src/api.ts`)
- Added special handling for `error` events with undefined/null data
- Gracefully ignores these (likely server closing connection after workflow_failed)

#### 2. Subagent Event Support
- Added SSE event types: `subagent_tool_started`, `subagent_tool_completed`, `subagent_progress`
- Added handlers in store for these events (will work IF MAF starts streaming them)

#### 3. Backend Logging (`src/agent-research-orchestrator/orchestrator.py`)
- Added detailed logging to `create_subagent_stream_callback()` to understand what data is received
- Logs every update from subagent stream_callback including type, attributes, and content details

#### 4. Minor Fixes
- Fixed PlanPanel unique key warning by adding fallback ID generation

### Root Cause Analysis

Azure AI Foundry hosted agents (market-analyst, competitor-analyst, synthesizer) are **Foundry-hosted agents**. When they call MCP tools like `add_note`, the execution happens:

1. Orchestrator calls `market_analysis` tool → MAF invokes hosted agent
2. Hosted agent runs on Foundry server → calls `add_note` tool SERVER-SIDE
3. Tool result returns to hosted agent → agent generates response
4. Response streams back to orchestrator via `stream_callback`

The `stream_callback` only receives **text tokens** from the final response, NOT the intermediate tool calls that happened server-side.

### Potential Solutions (Future Work)

1. **Enhanced Trace Polling**: Ensure subagent tool calls are logged to App Insights with proper operation_Id correlation
2. **Azure AI SDK Updates**: Check if newer SDK versions expose tool calls in stream_callback
3. **Hybrid Approach**: Poll App Insights more aggressively during subagent execution windows

---

## 2024-12-04: Activity Panel UX Enhancements

### Context
Enhanced the Activity panel to show richer information from SSE events, including preview text from tool outputs and consistent color coding per agent.

### Changes Made

#### 1. Activity Interface (`src/web-research/src/types.ts`)
- Added `agentColor?: string` field for consistent agent color coding

#### 2. Store Enhancements (`src/web-research/src/store.ts`)
- Added `getAgentColor()` helper that assigns consistent colors to agents:
  - Orchestrator: blue
  - Market Analyst: purple
  - Competitor Analyst: orange
  - Location Scout: cyan
  - Finance Analyst: green
  - Synthesizer: pink
- Added `extractInputPreview()` helper to extract preview text from tool input args
- Added `extractOutputPreview()` helper to extract preview text from tool outputs (handles both string and array formats from Azure AI Agent Service)
- Updated all legacy event handlers to include:
  - `preview` field with truncated content (100-200 chars)
  - `agentColor` field for consistent coloring

#### 3. ActivityPanel Component (`src/web-research/src/components/ActivityPanel.tsx`)
- Added `getAgentColorClass()` function mapping color names to Tailwind classes
- Updated `ActivityItem` to display preview text with styled container:
  - Italic text with muted color
  - Light background with left border
  - 2-line clamp for long content
- Actor names now use agent-specific colors when available

### Design Rationale
- Preview text helps users understand what agents are doing without expanding details
- Consistent agent colors make it easier to track which agent is performing actions
- Tailwind requires explicit class names (no dynamic generation), hence the color mapping

### Build Verification
- Frontend builds successfully with no TypeScript errors

---

## 2024-12-03: Frontend Migration to Trace-Based Architecture

### Context
Completed full frontend refactoring to support the new trace-based SSE event architecture (ADR-005). Removed all legacy event types that are no longer emitted by the backend.

### Changes Made

#### 1. Types (`src/web-research/src/types.ts`)
- Removed 20+ legacy SSE event types (AGENT_*, SUBAGENT_*, SCRATCHPAD_*, SYNTHESIS_*, TOOL_CALL_*)
- New simplified types:
  - `SSEEventType`: 7 trace-based events (workflow_started, trace_span_started, trace_span_completed, trace_tool_call, heartbeat, workflow_completed, workflow_failed)
  - `ActivityItem`: unified type for timeline items (agent_delegation, tool_call, status)
  - `TraceEventData`: trace-specific event payload types

#### 2. API Client (`src/web-research/src/api.ts`)
- Replaced legacy event listeners with new trace event handlers
- Listens for: workflow_started, trace_span_started, trace_span_completed, trace_tool_call, heartbeat, workflow_completed, workflow_failed

#### 3. Store (`src/web-research/src/store.ts`)
- Added `activityItems` array for timeline visualization
- Added `handleTraceEvent()` that parses trace events into `ActivityItem` objects
- `parseTraceToActivity()` extracts agent names and tool names from span_name
- Handles span correlation via span_id for start/complete pairing

#### 4. ActivityPanel (`src/web-research/src/components/ActivityPanel.tsx`)
- New component replacing ChatPanel.tsx
- Timeline visualization with icons:
  - Users icon for agent delegations
  - Wrench icon for tool calls
  - CheckCircle/XCircle for status events
- Formats span names for readability (e.g., "MarketAnalyst.run" → "Market Analyst")

#### 5. Documentation
- Updated `src/web-research/README.md` with new architecture
- Updated `specs/services/agent-research-orchestrator/contracts/sse-events.yaml` - removed all deprecated events

#### 6. Backend Models (`src/agent-research-orchestrator/models.py`)
- Simplified `SSEEventType` enum to 7 events
- Removed deprecated model classes (ToolCallStartedData, SubagentToolStartedData, ScratchpadUpdatedData, etc.)
- Added new typed models: WorkflowStartedData, WorkflowCompletedData, WorkflowFailedData, HeartbeatData

### Environment Variables
- `ENABLE_SENSITIVE_DATA=true` - enables logging of prompts/responses in traces
- `LOG_ANALYTICS_WORKSPACE_ID=8ed0a244-d2bb-4a56-ab10-3f6d0ab251dc` - for trace polling

### Build Verification
- Frontend builds successfully with no TypeScript errors
- All modules transformed correctly (1547 modules)

---

## 2024-12-02: Application Insights Trace Polling for SSE Events (ADR-005 Phase 2-3)

### Context
Implemented the trace polling mechanism described in ADR-005 Phase 2-3. This enables real-time visibility into subagent tool calls by polling Application Insights and streaming the results as SSE events.

### Problem Solved
- MAF's `stream_callback` only receives text tokens from Foundry-hosted agents
- Subagent tool calls (e.g., market-analyst calling mcp-scratchpad.add_note) execute server-side
- Without this, the UI has no visibility into what subagents are doing

### Implementation Details

#### 1. New Module: `trace_poller.py`
Created `AppInsightsTracePoller` class that:
- Polls Log Analytics Workspace every 2 seconds using Azure Monitor Query SDK
- Queries `union traces, dependencies` filtered by `operation_Id`
- Parses traces into typed `TraceEvent` objects
- Converts traces to SSE events: `trace_span_started`, `trace_span_completed`, `trace_tool_call`
- Deduplicates spans by span ID to prevent duplicate events
- Logs INFO-level messages for troubleshooting (can be reduced later)

KQL query structure:
```kusto
union 
    (traces | where operation_Id == "{operation_id}" | where timestamp > datetime({since})...),
    (dependencies | where operation_Id == "{operation_id}" | where timestamp > datetime({since})...)
| order by timestamp asc
| take 100
```

#### 2. API Integration (`api.py`)
Updated `event_generator()` to run workflow events and trace polling in parallel:
- Initializes `AppInsightsTracePoller` if `LOG_ANALYTICS_WORKSPACE_ID` is configured
- Runs both workflow generator and trace poller concurrently
- Emits trace events alongside workflow events
- Does a final trace poll after workflow completes (with 2s delay for ingestion)
- Properly cleans up poller on disconnect/error

#### 3. New SSE Event Types (`models.py`)
Added three new event types per ADR-005 spec:
- `TRACE_SPAN_STARTED` - Span began (from App Insights)
- `TRACE_SPAN_COMPLETED` - Span ended with duration/success
- `TRACE_TOOL_CALL` - MCP tool call detected in traces

Data models: `TraceSpanStartedData`, `TraceSpanCompletedData`, `TraceToolCallData`

#### 4. Configuration (`config.py`)
New settings:
- `LOG_ANALYTICS_WORKSPACE_ID` - GUID of Log Analytics Workspace
- `TRACE_POLLING_ENABLED` - Boolean toggle (default: true)
- `TRACE_POLLING_INTERVAL_SECONDS` - Poll interval (default: 2.0)
- `trace_polling_configured` property - checks if polling is ready

#### 5. Health Check
Added `/health/detailed` endpoint showing trace polling status.

### Logging
Added extensive INFO-level logging for troubleshooting:
- Poller initialization with workspace ID and operation ID
- Each poll count and number of new events found
- Agent invocation and tool call detection
- Final poll results
- Cleanup confirmation

### Expected Latency
- App Insights ingestion: 2-5 seconds
- Polling interval: 2 seconds
- Total latency: 4-7 seconds from agent action to SSE event

### Configuration Required
Set in `.env`:
```bash
LOG_ANALYTICS_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TRACE_POLLING_ENABLED=true
TRACE_POLLING_INTERVAL_SECONDS=2.0
```

Get workspace ID from Terraform: `terraform output log_analytics_workspace_id`

### Testing Notes
To verify traces are working:
1. Start a research session
2. Check logs for "Trace poller initialized" and "poll complete" messages
3. Look for `trace_tool_call` events in SSE stream
4. Query App Insights directly to verify traces exist

### Next Steps (ADR-005 Phase 4)
- [ ] Update frontend to handle new trace event types
- [ ] Add trace timeline component to UI
- [ ] Test end-to-end flow with all agent types

---

## 2024-01-XX: OpenTelemetry Integration for Real-Time Agent Observability (ADR-005)

### Context
Implemented OpenTelemetry-based tracing to enable real-time visibility into agent tool calls and subagent execution. This addresses the limitation that `stream_callback` in MAF doesn't capture tool calls from Foundry-hosted agents (tools execute server-side).

### Implementation Details

#### 1. Telemetry Module (`src/agent-research-orchestrator/telemetry.py`)
- Created centralized telemetry configuration module
- Uses `azure-monitor-opentelemetry` for Azure Application Insights export
- Configures auto-instrumentation for:
  - FastAPI requests/responses
  - HTTPX outgoing HTTP calls (MCP server communication)
  - AIAgentsInstrumentor (if available) for MAF agent tracing
- Provides helper functions: `get_tracer()`, `set_session_context()`, `set_agent_context()`, `set_tool_context()`
- Telemetry is configured once at startup via `configure_telemetry()`

#### 2. Session-Level Tracing (`src/agent-research-orchestrator/api.py`)
- `start_session` endpoint creates a parent span `research_session` that encompasses the entire workflow
- The span's `operation_id` (trace_id) is emitted in the first SSE event (`workflow_started`)
- All child spans (tool calls, subagent invocations) are correlated via this operation_id
- Frontend can use operation_id to query App Insights for real-time trace data

#### 3. Tool Call Tracing (`src/agent-research-orchestrator/orchestrator.py`)
- `create_tool_call_middleware` now creates OpenTelemetry spans for each tool call
- Span attributes include:
  - `tool.name`, `tool.call_id`, `tool.call_number`
  - `tool.type` (subagent, scratchpad_write, scratchpad_read, mcp)
  - `subagent.name` for agent-as-tool invocations
  - `session.id` for correlation
  - `tool.execution_time_ms` for performance tracking
- Errors are recorded with `span.record_exception()`

#### 4. MCP Scratchpad Telemetry (`src/mcp-scratchpad/main.py`)
- Added `configure_azure_monitor()` call when `APPLICATIONINSIGHTS_CONNECTION_STRING` is set
- All MCP tool calls will be traced to the same App Insights instance

### Dependencies Added
- `azure-monitor-opentelemetry>=1.6.0` - Azure Monitor exporter
- `azure-monitor-query>=1.3.0` - For future trace polling API
- `opentelemetry-instrumentation-fastapi>=0.50b0` - FastAPI auto-instrumentation
- `opentelemetry-instrumentation-httpx>=0.50b0` - HTTPX auto-instrumentation

### Configuration Required
Set `APPLICATIONINSIGHTS_CONNECTION_STRING` environment variable with the connection string from your Azure Application Insights resource. Without this, tracing is disabled with a warning.

### Architecture Decision
See [ADR-005: Real-time Agent Observability via OpenTelemetry and Application Insights](../specs/platform/decisions/ADR-005-realtime-agent-observability.md) for the full decision context and alternatives considered.

### Next Steps
1. Test that traces appear correctly in Application Insights
2. Implement backend trace polling endpoint (`GET /research/sessions/{id}/traces`)
3. Add KQL query logic to fetch traces by operation_id
4. Update frontend to poll traces and display agent activity timeline

---

## 2024-01-XX: Terraform - Azure AI Foundry Application Insights Connection

### Context
The Foundry portal's Tracing UI showed "No agents connected to Application Insights" despite diagnostic settings being configured. Investigation revealed that diagnostic settings only send logs/metrics to Log Analytics - a separate **connection** resource is required to enable the Tracing UI and `project_client.telemetry.get_application_insights_connection_string()` functionality.

### Solution
Added an `azapi_resource` for `Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview` in `foundry.tf`:

```terraform
resource "azapi_resource" "foundry_appinsights_connection" {
  type      = "Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview"
  name      = "${var.project_name}-appinsights"
  parent_id = azapi_resource.ai_foundry_account.id

  body = {
    properties = {
      category      = "AppInsights"
      target        = azurerm_application_insights.main.id
      authType      = "ApiKey"
      isSharedToAll = true
      credentials = {
        key = azurerm_application_insights.main.connection_string
      }
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_application_insights.main.id
      }
    }
  }
}
```

### Key Findings
- **Category**: Must be `"AppInsights"` (not `"ApplicationInsights"` as one might expect)
- **Target**: Resource ID of the Application Insights instance
- **AuthType**: `"ApiKey"` with the connection string as the key
- **Connection vs DiagnosticSettings**: DiagnosticSettings routes logs → Log Analytics; Connection enables SDK telemetry features

### Reference
- [GitHub: foundry-samples/connection-application-insights.bicep](https://github.com/azure-ai-foundry/foundry-samples/tree/main/samples/microsoft/infrastructure-setup/01-connections/connection-application-insights.bicep)
- [MS Learn: Foundry Connections](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/connections-add)

---

## 2024-01-XX: RBAC for Application Insights Tracing

### Context
Added RBAC role assignments required for Foundry tracing integration per [MS Learn documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/trace-application).

### Roles Added (`deploy/azure/terraform/rbac.tf`)

| Role | Principal | Scope | Purpose |
|------|-----------|-------|---------|
| Log Analytics Reader | Current User | Application Insights | View traces in Foundry portal Tracing UI |
| Monitoring Metrics Publisher | Container Apps MI | Application Insights | Publish telemetry from Container Apps |
| Monitoring Metrics Publisher | Foundry Project MI | Application Insights | Publish telemetry from Foundry-hosted agents |
| Monitoring Metrics Publisher | Foundry Account MI | Application Insights | Publish telemetry from Foundry account |

### Key Role IDs
- **Log Analytics Reader**: `73c42c96-874c-492b-b04d-ab87d138a893`
- **Monitoring Metrics Publisher**: `3913510d-42f4-4e42-8a64-420c390055eb`

### Reference
- [MS Learn: Trace Application](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/trace-application)
- [MS Learn: Log Analytics Reader Role](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/manage-access?tabs=portal#log-analytics-reader)
