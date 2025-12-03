/**
 * Type definitions for the web-research frontend.
 *
 * ADR-007: UI events are generated directly by the orchestrator middleware,
 * providing real-time updates. Trace events are kept for observability only.
 */

// === Session & Workflow Types ===

export type SessionStatus =
  | 'idle'
  | 'pending'
  | 'preparing'  // MCP tools being injected, agents being configured
  | 'running'     // Dynamic research workflow started
  | 'completed'
  | 'failed';

export interface ResearchSession {
  sessionId: string;
  query: string;
  status: SessionStatus;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  operationId?: string; // Trace correlation ID
}

// === Plan/Task Types (The Checklist) ===

export type TaskStatus = 'pending' | 'in-progress' | 'completed' | 'failed' | 'skipped' | 'todo' | 'blocked' | 'done';

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
  sourceUrl?: string;
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

// === Activity Message Types ===

/**
 * Activity types for the timeline view.
 * Maps trace events to user-friendly activities.
 */
export type ActivityType =
  | 'workflow_start'      // Session/workflow began
  | 'workflow_complete'   // Workflow finished successfully
  | 'workflow_error'      // Workflow failed
  | 'agent_delegation'    // Orchestrator delegating to subagent
  | 'agent_working'       // Agent is processing
  | 'agent_complete'      // Agent finished its work
  | 'tool_call'           // Agent calling an MCP tool
  | 'scratchpad_update'   // Note/draft/plan update detected
  | 'system';             // System messages

/**
 * A single activity item in the timeline.
 */
export interface Activity {
  id: string;
  type: ActivityType;
  timestamp: string;
  
  // Who initiated this activity
  actor: string;          // e.g., "Orchestrator", "Market Analyst"
  
  // What happened (short description)
  action: string;         // e.g., "Delegating to Market Analyst"
  
  // Optional details
  target?: string;        // e.g., tool name, target agent
  durationMs?: number;    // If completed, how long it took
  success?: boolean;      // If completed, was it successful
  details?: string;       // Additional context (truncated tool args, etc.)
  preview?: string;       // Preview of content (tool output, response text)
  agentColor?: string;    // Color hint for the agent (e.g., "blue", "purple")
  
  // Trace correlation
  operationId?: string;
  spanId?: string;
}

// === Scratchpad State (Combined) ===

export interface ScratchpadState {
  plan: Task[];
  notes: Note[];
  draft: DraftSection[];
  questions: Question[];
}

// === SSE Event Types (ADR-007: Direct orchestrator events) ===

export type SSEEventType =
  // Workflow lifecycle
  | 'workflow_started'    // Initial event with operation_id
  | 'workflow_completed'
  | 'workflow_failed'
  // Agent events (primary - from orchestrator)
  | 'session_started'
  | 'agent_started'
  | 'agent_progress'
  | 'agent_completed'
  | 'agent_response'
  // Tool call events (primary - from middleware)
  | 'tool_call_started'
  | 'tool_call_completed'
  // Subagent events (primary - from stream_callback)
  | 'subagent_tool_started'
  | 'subagent_tool_completed'
  | 'subagent_progress'
  // Scratchpad events (primary - from middleware)
  | 'scratchpad_updated'
  // Synthesis events
  | 'synthesis_completed'
  // Keep-alive
  | 'heartbeat'
  // Error fallback
  | 'error'
  // Trace events (observability only - not actively used for UI)
  | 'trace_span_started'
  | 'trace_span_completed'
  | 'trace_tool_call';

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

// === Trace Event Data Types ===

export interface WorkflowStartedData {
  session_id: string;
  operation_id: string;
  trace_polling_enabled: boolean;
  timestamp: string;
}

export interface WorkflowCompletedData {
  synthesis?: string;
  total_tool_calls?: number;
  total_time_ms?: number;
}

export interface WorkflowFailedData {
  error: string;
  error_type?: string;
}

export interface TraceSpanStartedData {
  span_name: string;
  agent_name?: string;
  operation_id: string;
  timestamp: string;
}

export interface TraceSpanCompletedData {
  span_name: string;
  agent_name?: string;
  operation_id: string;
  timestamp: string;
  duration_ms: number;
  success?: boolean;
}

export interface TraceToolCallData {
  span_name: string;
  tool_name: string;
  agent_name?: string;
  mcp_server?: string;
  operation_id: string;
  timestamp: string;
  duration_ms?: number;
  success?: boolean;
}

// === Application State ===

export interface AppState {
  // Session
  session: ResearchSession | null;

  // Scratchpad pillars
  scratchpad: ScratchpadState;

  // Activity timeline (replaces chat messages)
  activities: Activity[];

  // Final synthesis report (full markdown from Synthesizer)
  finalReport: string | null;

  // UI state
  isConnected: boolean;
  activePanel: 'activity' | 'plan' | 'notes' | 'draft' | 'final';
  showQuestionModal: boolean;
}

// === Demo State Snapshot ===

/**
 * Serializable snapshot of the application state for demo purposes.
 * Used to save/load a complete research session state.
 */
export interface DemoStateSnapshot {
  version: number;
  exportedAt: string;
  session: ResearchSession;
  scratchpad: ScratchpadState;
  activities: Activity[];
  finalReport: string | null;
}
