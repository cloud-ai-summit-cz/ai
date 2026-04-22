# web-research

React frontend for the Cofilot Research demo, providing a real-time visualization of the multi-agent research workflow.

## Features

- **Modern UI**: ChatGPT-inspired grayscale design
- **Live Updates**: SSE-based real-time updates from trace polling (ADR-005)
- **Scratchpad Visualization**:
  - **Activity**: Agent workflow timeline showing delegations, tool calls, and completions
  - **Plan**: Task checklist with status tracking
  - **Notes**: Append-only research findings
  - **Draft**: Live document being built by agents
- **Human-in-the-Loop**: Answer agent questions via modal interface

## Architecture

The frontend uses a **trace-based architecture** where:
1. Backend polls Application Insights for OpenTelemetry traces
2. Trace events are streamed via SSE to the frontend
3. Frontend parses trace spans into user-friendly activity items

This provides visibility into subagent tool calls that can't be captured via MAF's stream_callback.

### SSE Event Types

| Event | Description |
|-------|-------------|
| `workflow_started` | Session initialized with operation_id |
| `workflow_completed` | Workflow finished successfully |
| `workflow_failed` | Workflow encountered an error |
| `trace_span_started` | Agent/operation started (from App Insights) |
| `trace_span_completed` | Agent/operation completed with duration |
| `trace_tool_call` | MCP tool call detected |
| `heartbeat` | Keep-alive signal |

## Development

### Prerequisites

- Node.js 20+
- npm 10+

### Quick Start

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:3000)
npm run dev
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Research orchestrator API URL | `http://localhost:8000` |

## Build & Deploy

### Local Build

```bash
npm run build
npm run preview
```

### Docker

```bash
# Build image
docker build -t web-research .

# Run container
docker run -p 8080:80 \
  -e VITE_API_URL=https://orchestrator.example.com \
  web-research
```

## Project Structure

```
src/
├── components/       # React components
│   ├── ActivityPanel.tsx   # Workflow timeline view
│   ├── PlanPanel.tsx       # Task checklist
│   ├── NotesPanel.tsx      # Research notes feed
│   ├── DraftPanel.tsx      # Document viewer
│   ├── QuestionsPanel.tsx  # Human-in-the-loop UI
│   ├── QueryInput.tsx      # Landing page search
│   ├── Header.tsx          # App header
│   └── PanelTabs.tsx       # Navigation tabs
├── views/            # Page-level components
│   └── Workspace.tsx       # Main workspace layout
├── store.ts          # Zustand state management
├── api.ts            # API client with SSE handling
├── types.ts          # TypeScript definitions
├── App.tsx           # Root component
└── main.tsx          # Entry point
```

## Connecting to Backend

1. Ensure the `agent-research-orchestrator` is running
2. Ensure `LOG_ANALYTICS_WORKSPACE_ID` is configured for trace polling
3. Set `VITE_API_URL` to the orchestrator's URL (or use proxy in dev)
4. The app will:
   - POST to `/research/sessions` to create sessions
   - GET SSE from `/research/sessions/{id}/start` for trace events
   - Poll `/research/sessions/{id}/scratchpad/*` for state updates
