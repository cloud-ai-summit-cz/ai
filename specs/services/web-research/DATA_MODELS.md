# Service Data Models: web-research

This service consumes data models from the `mcp-scratchpad` and `agent-research-orchestrator`. It maintains a client-side reflection of these models.

## Schema Inventory

| Name | Type | Owner | Source of Truth |
| --- | --- | --- | --- |
| `ResearchSession` | Client State | web-research | Orchestrator (via API) |
| `OrchestratorEvent` | Event | research-orchestrator | Orchestrator (via SSE) |
| `ScratchpadState` | Data Structure | mcp-scratchpad | Orchestrator (via SSE snapshot) |

## Detailed Schemas

### ResearchSession
Client-side store for the active session.

```typescript
interface ResearchSession {
  sessionId: string;
  status: 'initializing' | 'active' | 'paused' | 'completed' | 'error';
  query: string;
  messages: ChatMessage[];
  scratchpad: ScratchpadState;
  pendingQuestions: Question[];
}
```

### ScratchpadState
Mirror of the backend Scratchpad architecture.

```typescript
interface ScratchpadState {
  // The "Plan" Pillar
  plan: {
    tasks: Array<{
      id: string;
      description: string;
      status: 'pending' | 'in-progress' | 'completed' | 'failed';
      assignedTo?: string;
    }>;
  };
  
  // The "Notes" Pillar
  notes: Array<{
    id: string;
    content: string; // Markdown
    author: string;
    timestamp: string;
    tags: string[];
  }>;
  
  // The "Draft" Pillar
  draft: {
    sections: Record<string, {
      title: string;
      content: string; // Markdown
      lastUpdated: string;
    }>;
  };
}
```

### OrchestratorEvent
SSE payloads received from the backend.

```typescript
type OrchestratorEvent = 
  | { type: 'session_created', payload: { sessionId: string } }
  | { type: 'state_update', payload: { scratchpad: Partial<ScratchpadState> } }
  | { type: 'message', payload: { from: string, content: string, type: 'info' | 'error' } }
  | { type: 'question_asked', payload: Question }
  | { type: 'session_completed', payload: { reportUrl: string } };
```

### Question
Structure for human-in-the-loop interaction.

```typescript
interface Question {
  id: string;
  text: string;
  context?: string;
  options?: string[]; // For multiple choice
  answered: boolean;
}
```
