# Implementation Log

Technical decisions and implementation notes for the Copilot AI Platform project.

## 2025-12-06: Rate Limit Retry Middleware for Agent Framework

### Context
Azure OpenAI API returns 429 (Too Many Requests) errors when rate limits are exceeded. These errors were causing the entire workflow to fail instead of gracefully retrying.

### Solution
Implemented `RateLimitRetryMiddleware` using Microsoft Agent Framework's `ChatMiddleware` pattern. This follows the official middleware architecture documented at:
- https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-middleware
- https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/middleware

### Changes Made

#### 1. New Module: `src/agent-research-orchestrator/retry_middleware.py`
- `RateLimitRetryMiddleware`: ChatMiddleware class for 429 error handling
- Implements exponential backoff with jitter (Microsoft recommended pattern)
- Extracts `Retry-After` header from API responses when available
- Configurable: max_retries, initial_delay, max_delay, exponential_base, jitter
- Default: 5 retries, 2s initial delay, 60s max delay, 2x exponential base

#### 2. Updated: `src/agent-research-orchestrator/orchestrator.py`
- Added import for `RateLimitRetryMiddleware`
- Applied middleware to main orchestrator `ChatAgent`
- Applied middleware to Foundry sub-agents via `_create_foundry_agent()`

#### 3. New Files: `src/agent-*/standalone/a2a/maf/retry_middleware.py` (5 files)
- Created identical retry middleware for each standalone subagent:
  - `agent-market-analyst`
  - `agent-competitor-analyst`
  - `agent-location-scout`
  - `agent-finance-analyst`
  - `agent-synthesizer`

#### 4. Updated: `src/agent-*/standalone/a2a/maf/agent.py` (5 files)
- Added import for `RateLimitRetryMiddleware`
- Applied middleware to each subagent's `ChatAgent` via `responses_client.create_agent()`

### Configuration
```python
retry_middleware = RateLimitRetryMiddleware(
    max_retries=5,       # Max retry attempts
    initial_delay=2.0,   # Initial delay in seconds
    max_delay=60.0,      # Maximum delay cap
    exponential_base=2.0, # Backoff multiplier
    jitter=True,         # Add randomness to prevent thundering herd
)
```

### Retry Logic
- Delay formula: `min(initial_delay * (2 ^ attempt), max_delay)`
- Jitter adds 0-25% random variation
- Respects `Retry-After` header from API if present
- Logs all retry attempts at WARNING level

### Reference
- Azure retry patterns: https://learn.microsoft.com/en-us/azure/architecture/patterns/retry
- Azure OpenAI error handling: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/supported-languages#error-handling

---

## 2025-01-XX: ADR-007 - Direct Orchestrator Events for UI (Reverting Trace-Based SSE)

### Context
Implemented ADR-007 to revert from trace-based SSE events to direct orchestrator-generated events for the UI. The trace polling approach (ADR-005) had 2-5 second latency due to App Insights ingestion delays, making UI updates feel sluggish.

### Changes Made

#### 1. Documentation
- Created `specs/platform/decisions/ADR-007-direct-orchestrator-events-for-ui.md`
- Updated `specs/services/agent-research-orchestrator/contracts/sse-events.yaml` to document direct events as primary

#### 2. Backend (`src/agent-research-orchestrator/`)
- **api.py**: Removed trace poller integration from `event_generator()`, simplified to only emit workflow events from orchestrator
- **models.py**: Updated `SSEEventType` enum - removed "Legacy" labels from direct events, marked trace events as observability-only

#### 3. Frontend
- No changes needed - `store.ts` already handled both trace and direct events

### Architecture After Change
```
Orchestrator → SSE Stream → UI        (real-time, <100ms latency)
     ↓
OpenTelemetry → App Insights          (observability, 2-5s latency, for dashboards)
```

### What's Kept
- OpenTelemetry spans in orchestrator middleware (for App Insights dashboards)
- `trace_poller.py` module (dormant, kept for potential future use)
- Trace event types in models (marked as observability-only)

### What's Removed
- Trace polling from SSE event generator
- Complex parallel task management in api.py
- UI dependency on App Insights availability

### Reference
- ADR-007: `specs/platform/decisions/ADR-007-direct-orchestrator-events-for-ui.md`
- Related: ADR-005 (partially superseded), ADR-006 (MCP tools in orchestrator)

---

## 2025-12-02: Fix Session Isolation - Remove Static Scratchpad Registration

### Context
MCP Scratchpad was incorrectly registered as a static tool in all Foundry Native agent provision scripts (`market-analyst`, `competitor-analyst`, `synthesizer`). This violated the session isolation architecture documented in `ARCHITECTURE.md`.

### The Problem
When the `project_connection_id` feature was implemented to satisfy Azure's security requirement about headers, the developer applied it uniformly to ALL MCP tools including scratchpad. This was incorrect because:

1. **Session Isolation Architecture** (per `ARCHITECTURE.md`) requires scratchpad to be added **dynamically by the orchestrator** with `X-Session-ID` headers
2. Static registration means agents get scratchpad tools **without** session headers
3. This breaks session isolation - agents could potentially read/write data from other sessions

### The Fix
Removed `mcp-scratchpad` from static tool registration in all provision.py files:
- `src/agent-competitor-analyst/provision.py` - Now only registers: web_search, business_registry
- `src/agent-market-analyst/provision.py` - Now only registers: web_search, demographics  
- `src/agent-synthesizer/provision.py` - Now only registers: calculator

The orchestrator in `agent-research-orchestrator/orchestrator.py` correctly adds scratchpad dynamically via `SessionScopedMCPTool` which injects `X-Session-ID` headers.

### Static vs Dynamic MCP Tools

| Tool | Registration | Why |
|------|-------------|-----|
| mcp-scratchpad | **Dynamic** (orchestrator) | Requires X-Session-ID header for session isolation |
| mcp-web-search | Static (provision.py) | No session-specific data |
| mcp-demographics | Static (provision.py) | Reference data, no session state |
| mcp-business-registry | Static (provision.py) | Reference data, no session state |
| mcp-calculator | Static (provision.py) | Stateless calculations |

### Deployment Steps
1. Re-run agent provisioning for each agent:
   ```bash
   cd src/agent-market-analyst && uv run python provision.py create
   cd src/agent-competitor-analyst && uv run python provision.py create
   cd src/agent-synthesizer && uv run python provision.py create
   ```

### Reference
- `specs/platform/ARCHITECTURE.md` - "Session Isolation Architecture" section
- `src/agent-research-orchestrator/orchestrator.py` - `SessionScopedMCPTool` class

---

## 2025-01-XX: Project Connections for Static MCP Tools (project_connection_id)

### Context
Agent provisioning was failing with `ValidationError: "Headers that can include sensitive information are not allowed in the headers property for MCP tools. Use project_connection_id instead."` This Azure AI Foundry requirement means sensitive auth headers (like `Authorization: Bearer xxx`) must be stored in Foundry project connections rather than passed directly in `MCPTool` headers.

### What is project_connection_id?
A **project connection** in Azure AI Foundry securely stores:
- **target**: MCP server URL (e.g., `https://ca-mcp-demographics.xxx.azurecontainerapps.io/mcp`)
- **authType**: Authentication method (`CustomKeys` for API key auth)
- **credentials**: Secret values (e.g., `{"Authorization": "Bearer dev-xxx-key"}`)
- **category**: Set to `RemoteTool` for MCP servers

When an agent's `MCPTool` references `project_connection_id`, Foundry:
1. Retrieves the connection at runtime
2. Extracts URL and credentials
3. Injects auth headers automatically

### Benefits
- ✅ **UI Visibility**: Tools appear in Foundry portal connected resources
- ✅ **Secure Secrets**: Credentials stored in Azure, not in agent definition
- ✅ **Azure Compliance**: Required for production - headers block disallowed

### Implementation

#### 1. Terraform: Created project connections (`foundry.connections.tf`)
```terraform
resource "azapi_resource" "mcp_connection_demographics" {
  type      = "Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview"
  name      = "mcp-demographics"
  parent_id = azapi_resource.ai_foundry_project.id

  body = {
    properties = {
      authType      = "CustomKeys"
      category      = "RemoteTool"
      target        = "https://${azapi_resource.capp_mcp_demographics.output.properties.configuration.ingress.fqdn}/mcp"
      isSharedToAll = true
      credentials = {
        keys = {
          Authorization = "Bearer ${var.mcp_auth_token}"
        }
      }
      metadata = {
        ApiType     = "MCP"
        ServiceName = "demographics"
      }
    }
  }
}
```

Created connections for: `mcp-scratchpad`, `mcp-business-registry`, `mcp-government-data`, `mcp-demographics`

#### 2. Python provision.py: Updated all agents to use project_connection_id
```python
# Before (BLOCKED):
MCPTool(
    server_label="demographics",
    server_url=settings.mcp_demographics_url,
    headers={"Authorization": f"Bearer {settings.mcp_auth_token}"},  # ❌
)

# After:
MCPTool(
    server_label="demographics",
    server_url=settings.mcp_demographics_url,
    project_connection_id="mcp-demographics",  # ✅
)
```

Updated agents: market-analyst, competitor-analyst, synthesizer

#### 3. Terraform outputs
Added outputs for MCP URLs and connection names for reference.

### Files Changed
- `deploy/azure/terraform/foundry.connections.tf` - NEW: 4 project connections
- `deploy/azure/terraform/outputs.tf` - Added MCP URL and connection name outputs
- `src/agent-market-analyst/provision.py` - Use project_connection_id
- `src/agent-competitor-analyst/provision.py` - Use project_connection_id
- `src/agent-synthesizer/provision.py` - Use project_connection_id

### Deployment Steps
1. Run `terraform apply` to create the project connections
2. Re-run agent provisioning: `uv run python provision.py create`

### Reference
- [MS Learn: MCP Authentication](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol-authentication)
- [MS Learn: Knowledge Retrieval with MCP](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/knowledge-retrieval)

---

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

## 2024-01-XX: MCP Tool Servers Implementation (Business Registry, Government Data, Demographics)

### Context
Implemented three new MCP tool servers to provide reference data for the research agents. These servers provide mock data for company information, regulatory requirements, and demographic data for European cities.

### Servers Implemented

| Server | Port | Purpose | Tools |
|--------|------|---------|-------|
| `mcp-business-registry` | 8012 | Company data, financials, industry players | search_companies, get_company_profile, get_company_financials, get_company_locations, get_industry_players, get_company_news |
| `mcp-government-data` | 8013 | Permits, zoning, regulations, tax rates | get_business_permits, get_zoning_info, get_regulations, get_tax_rates, get_licensing_requirements, get_health_safety_codes, get_labor_laws |
| `mcp-demographics` | 8014 | Population, income, consumer behavior | get_population_stats, get_income_distribution, get_age_distribution, get_consumer_spending, get_lifestyle_segments, get_commuter_patterns |

### Architecture Pattern
- **Simple MCP Server**: No dynamic header handling (unlike mcp-scratchpad with session isolation)
- **StaticTokenVerifier**: Simple API key authentication via Bearer token
- **Mock Data Strategy**: Curated data for known cities (Vienna, Prague, Munich, Salzburg, Brno) + seeded random generation for flexibility
- **Seeded Randomization**: Uses MD5 hash of location string for consistent yet flexible mock data generation

### Files Created Per Server
- `config.py` - Settings with port, API key, debug flag
- `models.py` - Pydantic data models
- `mock_data.py` - Curated and generated mock data
- `server.py` - FastMCP server with tool definitions
- `main.py` - Entry point with Azure Monitor telemetry
- `pyproject.toml` - Dependencies
- `Dockerfile` - Container definition
- `README.md` - Documentation

### Infrastructure Updates

#### Terraform (`deploy/azure/terraform/`)
- Added `capp.mcp-business-registry.tf` - Container App for business registry
- Added `capp.mcp-government-data.tf` - Container App for government data
- Added `capp.mcp-demographics.tf` - Container App for demographics
- Updated `locals.tf` - Added image references for new containers

#### Build Configuration (`deploy/azure/build-config.yaml`)
- Added mcp-business-registry, mcp-government-data, mcp-demographics to container builds

### Agent Provisioning Updates

Updated Foundry Native agents to include MCP tools at provisioning time (shows in Foundry UI):

| Agent | MCP Tools |
|-------|-----------|
| market-analyst | scratchpad, web_search, demographics |
| competitor-analyst | scratchpad, web_search, business_registry |
| synthesizer | scratchpad, calculator |

#### Changes Made
- Updated `config.py` for each agent with MCP endpoint URLs
- Updated `provision.py` to use `MCPTool` from `azure.ai.projects.models`
- Tools configured with `require_approval="never"` and Bearer token auth

### Mock Data Highlights

#### Business Registry
- Coffee chains: Starbucks, Aida, Costa Coffee, Cafe Central, Kavárna, etc.
- Financial data: Revenue (€50M-€50B), employees (500-50k), growth rates
- Industry players: Top 10 competitors per region

#### Government Data
- Permits: Business license, food handling, health certificate, etc.
- Zoning: Commercial districts with specific regulations
- Tax rates: Corporate tax (19-25%), VAT (19-21%), local business tax
- Labor laws: Minimum wage, working hours, leave policies

#### Demographics
- Population stats: City/district population, density, growth rates
- Income: Median/mean income, purchasing power index, unemployment
- Age distribution: 7 age brackets with percentages
- Lifestyle segments: Urban Professionals, Students, Remote Workers, etc.
- Commuter patterns: Peak hours, foot traffic, transit modes

### Configuration

Environment variables for each server:
```bash
HOST=0.0.0.0
PORT=801X
API_KEY=dev-{service}-key
APPLICATIONINSIGHTS_CONNECTION_STRING=...  # Optional
DEBUG=false
```

### Reference
- Architecture spec: `specs/platform/ARCHITECTURE.md`
- Tool contracts: `specs/services/mcp-*/contracts/mcp-tools.json`

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
