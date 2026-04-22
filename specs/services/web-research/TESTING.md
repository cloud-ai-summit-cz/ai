# Service Testing Strategy: web-research

## Test Matrix

| Layer | Tools | Scope | Owner |
| --- | --- | --- | --- |
| **Unit** | Jest / Vitest | Utility functions, State reducers | Frontend Dev |
| **Component** | React Testing Library | Individual UI components (Chat bubble, Task item) | Frontend Dev |
| **E2E** | Playwright | Full user flows (Submit query -> See result) | QA / Dev |

## Scenarios

### 1. Research Initiation
- **Given** the user is on the landing page
- **When** they type "Analyze coffee market" and hit Enter
- **Then** the UI transitions to the Workspace view
- **And** a "Session Initialized" message appears in the chat

### 2. Real-time Updates
- **Given** a research session is active
- **When** the backend sends a `note_added` event via SSE
- **Then** the Notes panel automatically appends the new note without page reload

### 3. Human-in-the-loop
- **Given** the orchestrator pauses for a question
- **When** the `question_pending` event is received
- **Then** a modal appears with the question text
- **When** the user submits an answer
- **Then** the modal closes and the answer is posted to the chat stream

## Environments
- **Local**: `npm run dev` (Vite) with mock API or local backend.
- **CI**: Headless browser tests in GitHub Actions.
