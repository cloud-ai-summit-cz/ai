# Service Data Models: web-research

This service consumes data models from the `mcp-scratchpad` and `agent-research-orchestrator`. It maintains a client-side reflection of these models.

## Schema Inventory

| Name | Type | Owner | Source of Truth |
| --- | --- | --- | --- |
| `ResearchSession` | Client State | web-research | Orchestrator (via API) |
| `OrchestratorEvent` | Event | research-orchestrator | Orchestrator (via SSE) |
| `ScratchpadState` | Data Structure | mcp-scratchpad | Orchestrator (via SSE snapshot) |
| `Question` | Data Structure | mcp-scratchpad | Orchestrator (via polling) |
| `QuestionsResponse` | API Response | research-orchestrator | GET /questions endpoint |
| `AnswersRequest` | API Request | web-research | POST /answers endpoint |

## Detailed Schemas

### ResearchSession
Client-side store for the active session.

```typescript
interface ResearchSession {
  sessionId: string;
  status: 'initializing' | 'active' | 'awaiting_input' | 'completed' | 'error';
  query: string;
  messages: ChatMessage[];
  scratchpad: ScratchpadState;
  questions: Question[];
  workflowWaiting: boolean;  // True when orchestrator is blocked waiting for user input
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
  
  // The "Questions" Pillar (human-in-the-loop)
  questions: Question[];
}
```

### OrchestratorEvent
SSE payloads received from the backend.

```typescript
type OrchestratorEvent = 
  | { type: 'session_created', payload: { sessionId: string } }
  | { type: 'state_update', payload: { scratchpad: Partial<ScratchpadState> } }
  | { type: 'message', payload: { from: string, content: string, type: 'info' | 'error' } }
  | { type: 'question_added', payload: QuestionAddedEvent }
  | { type: 'awaiting_user_input', payload: AwaitingUserInputEvent }
  | { type: 'questions_answered', payload: QuestionsAnsweredEvent }
  | { type: 'session_completed', payload: { reportUrl: string } };

interface QuestionAddedEvent {
  question: Question;
}

interface AwaitingUserInputEvent {
  reason: string;
  blocking_question_ids: string[];
}

interface QuestionsAnsweredEvent {
  answered_ids: string[];
  workflow_resumed: boolean;
}
```

### Question
Structure for human-in-the-loop interaction.

```typescript
type QuestionPriority = 'low' | 'medium' | 'high' | 'blocking';

interface Question {
  id: string;
  question: string;        // The question text
  context: string;         // Why this information is needed
  askedBy: string;         // Agent that asked this question
  priority: QuestionPriority;
  askedAt: string;         // ISO timestamp
  answered: boolean;
  answer?: string;         // User's answer (if answered)
  answeredAt?: string;     // ISO timestamp (if answered)
}
```

### AnswersRequest
Request payload for submitting answers.

```typescript
interface AnswersRequest {
  answers: Array<{
    questionId: string;
    answer: string;
  }>;
}
```

### QuestionsResponse
Response from GET /questions endpoint.

```typescript
interface QuestionsResponse {
  sessionId: string;
  questions: Question[];
  pendingCount: number;
  answeredCount: number;
  hasBlockingPending: boolean;
  workflowWaiting: boolean;
}
```
