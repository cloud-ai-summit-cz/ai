/**
 * Type definitions for the web-research frontend.
 * 
 * Aligns with the backend SSE event models from agent-research-orchestrator.
 */

// === Session & Workflow Types ===

export type SessionStatus = 
  | 'idle'
  | 'pending' 
  | 'running' 
  | 'paused' 
  | 'completed' 
  | 'failed';

export interface ResearchSession {
  sessionId: string;
  query: string;
  status: SessionStatus;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

// === Plan/Task Types (The Checklist) ===

export type TaskStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped';

export interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  assignedTo?: string;
  completedAt?: string;
}

// === Notes Types (The Corkboard) ===

export interface Note {
  id: string;
  content: string;
  author: string;
  timestamp: string;
  tags: string[];
}

// === Draft Types (The Manuscript) ===

export interface DraftSection {
  id: string;
  title: string;
  content: string;
  lastUpdatedBy?: string;
  lastUpdatedAt?: string;
  version: number;
}

// === Questions Types (Human-in-the-Loop) ===

export interface Question {
  id: string;
  text: string;
  context?: string;
  askedBy: string;
  priority: 'high' | 'medium' | 'low';
  blocking: boolean;
  options?: string[];
  answer?: string;
  answeredAt?: string;
  createdAt: string;
}

// === Chat/Message Types ===

export type MessageType = 
  | 'system'
  | 'orchestrator'
  | 'agent'
  | 'tool'
  | 'user'
  | 'error';

export interface ChatMessage {
  id: string;
  type: MessageType;
  sender: string;
  content: string;
  timestamp: string;
  metadata?: {
    agentType?: string;
    toolName?: string;
    status?: 'started' | 'completed' | 'failed';
    duration?: number;
  };
}

// === Scratchpad State (Combined) ===

export interface ScratchpadState {
  plan: Task[];
  notes: Note[];
  draft: DraftSection[];
  questions: Question[];
}

// === SSE Event Types ===

export type SSEEventType =
  // Session lifecycle
  | 'session_started'
  | 'workflow_completed'
  | 'workflow_failed'
  // Agent events
  | 'agent_started'
  | 'agent_progress'
  | 'agent_thinking'
  | 'agent_completed'
  | 'agent_failed'
  // Tool events
  | 'tool_call_started'
  | 'tool_call_completed'
  | 'tool_call_failed'
  // Scratchpad events
  | 'scratchpad_updated'
  | 'scratchpad_snapshot'
  | 'question_added'
  | 'question_answered'
  // Synthesis
  | 'synthesis_started'
  | 'synthesis_progress'
  | 'synthesis_completed';

export interface SSEEvent {
  event_type: SSEEventType;
  session_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

// === Application State ===

export interface AppState {
  // Session
  session: ResearchSession | null;
  
  // Scratchpad pillars
  scratchpad: ScratchpadState;
  
  // Chat stream
  messages: ChatMessage[];
  
  // UI state
  isConnected: boolean;
  activePanel: 'chat' | 'plan' | 'notes' | 'draft';
  showQuestionModal: boolean;
}
