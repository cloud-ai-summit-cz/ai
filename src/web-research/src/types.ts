/**
 * Type definitions for the web-research frontend.
 *
 * Aligns with the backend SSE event models from agent-research-orchestrator.
 * Note: Backend uses snake_case, frontend uses camelCase. API layer handles mapping.
 */

// === Session & Workflow Types ===

export type SessionStatus =
  | 'idle'
  | 'pending'
  | 'running'
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

export type TaskStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped' | 'todo' | 'blocked';

export interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  assignedTo?: string;
  completedAt?: string;
  createdAt?: string;
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
    targetAgent?: string;  // For agent-to-agent delegations
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

// === SSE Event Types (matches backend SSEEventType enum) ===

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
  | 'agent_response'  // Subagent returned result → poll scratchpad
  // Tool events
  | 'tool_call_started'
  | 'tool_call_completed'
  | 'tool_call_failed'
  // Scratchpad events (deprecated - use polling)
  | 'scratchpad_updated'
  | 'scratchpad_snapshot'
  | 'question_added'
  | 'question_answered'
  // Synthesis
  | 'synthesis_started'
  | 'synthesis_progress'
  | 'synthesis_completed';

/**
 * SSE Event structure as received from the backend.
 * Note: Uses snake_case to match backend serialization.
 */
export interface SSEEvent {
  event_type: SSEEventType;
  session_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

// === SSE Event Data Types (matches backend *Data models) ===

export interface ToolCallStartedData {
  tool_name: string;
  tool_call_id: string;
  agent_name: string;
  input_args?: Record<string, unknown>;
}

export interface ToolCallCompletedData {
  tool_name: string;
  tool_call_id: string;
  agent_name: string;
  output?: unknown;
  execution_time_ms: number;
}

export interface ToolCallFailedData {
  tool_name: string;
  tool_call_id: string;
  agent_name: string;
  error: string;
  error_type?: string;
}

export interface ScratchpadUpdatedData {
  section_name: string;
  operation: 'created' | 'updated' | 'appended' | 'deleted';
  updated_by: string;
  content_preview?: string;
  appended_content?: string;
}

export interface ScratchpadSectionData {
  name: string;
  content: string;
  updated_by?: string;
  updated_at?: string;
}

export interface ScratchpadSnapshotData {
  sections: ScratchpadSectionData[];
  total_sections: number;
  iteration?: number;
  triggered_by?: string;
}

export interface QuestionAddedData {
  question_id: string;
  question: string;
  asked_by: string;
  context?: string;
  priority?: 'high' | 'medium' | 'low';
  blocking?: boolean;
  options?: string[];
}

export interface QuestionAnsweredData {
  question_id: string;
  answer: string;
  answered_at?: string;
}

// === Agent Event Data Types ===

export interface AgentStartedData {
  agent_name: string;
  task_description?: string;
}

export interface AgentProgressData {
  agent_name: string;
  chunk: string;
}

export interface AgentThinkingData {
  agent_name: string;
  message: string;
}

export interface AgentCompletedData {
  agent_name: string;
  result_summary?: string;
  execution_time_ms?: number;
}

export interface AgentFailedData {
  agent_name: string;
  error: string;
}

// === Session Event Data Types ===

export interface SessionStartedData {
  query: string;
  message?: string;
}

export interface WorkflowCompletedData {
  final_synthesis?: string;
  duration_seconds?: number;
}

export interface WorkflowFailedData {
  error: string;
  error_type?: string;
}

// === Synthesis Event Data Types ===

export interface SynthesisStartedData {
  message?: string;
}

export interface SynthesisProgressData {
  chunk: string;
}

export interface SynthesisCompletedData {
  final_report: string;
  sections_used?: string[];
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
