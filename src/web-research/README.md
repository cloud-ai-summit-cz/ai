# web-research

React frontend for the Cofilot Research demo, providing a real-time visualization of the multi-agent research workflow.

## Features

- **Modern UI**: ChatGPT-inspired grayscale design
- **Live Updates**: SSE-based real-time updates from the research orchestrator
- **Scratchpad Visualization**:
  - **Activity**: Agent communication and orchestration messages
  - **Plan**: Task checklist with status tracking
  - **Notes**: Append-only research findings
  - **Draft**: Live document being built by agents
- **Human-in-the-Loop**: Answer agent questions via modal interface

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
│   ├── ChatPanel.tsx       # Activity/message stream
│   ├── PlanPanel.tsx       # Task checklist
│   ├── NotesPanel.tsx      # Research notes feed
│   ├── DraftPanel.tsx      # Document viewer
│   ├── QuestionsPanel.tsx  # Human-in-the-loop UI
│   ├── QueryInput.tsx      # Landing page search
│   ├── Header.tsx          # App header
│   └── PanelTabs.tsx       # Navigation tabs
├── views/            # Page-level components
│   └── Workspace.tsx       # Main workspace layout
├── mocks/            # Mock data for development
│   └── data.ts             # Sample messages, tasks, notes
├── store.ts          # Zustand state management
├── types.ts          # TypeScript definitions
├── App.tsx           # Root component
└── main.tsx          # Entry point
```

## Mock Data

The app includes mock data for development without a backend:

1. Open `src/App.tsx`
2. Uncomment `loadMockData()` in the `useEffect`
3. Refresh to see populated workspace

The mock event stream simulates SSE updates at intervals.

## Connecting to Real Backend

1. Ensure the `agent-research-orchestrator` is running
2. Set `VITE_API_URL` to the orchestrator's URL
3. The app will:
   - POST to `/research/sessions` to create sessions
   - GET SSE from `/research/sessions/{id}/start`
   - POST to `/research/sessions/{id}/answers` for human input
