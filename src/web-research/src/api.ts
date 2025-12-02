/**
 * API client for the Research Orchestrator backend.
 *
 * Handles REST API calls and SSE event streaming.
 * Simplified for trace-based architecture (ADR-005).
 */

import type { ResearchSession, SSEEvent } from './types';

/**
 * Get the API base URL from environment or fall back to dev proxy.
 */
function getApiUrl(): string {
  // Runtime config injected by env.sh in Docker
  if (typeof window !== 'undefined' && (window as unknown as { env?: { API_URL?: string } }).env?.API_URL) {
    return (window as unknown as { env: { API_URL: string } }).env.API_URL;
  }
  // Development: use Vite proxy
  return '/api';
}

const API_URL = getApiUrl();

/**
 * API error with response details.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Create a new research session.
 *
 * @param query - The research query to investigate
 * @param context - Optional additional context
 * @returns The created session
 */
export async function createSession(
  query: string,
  context?: Record<string, unknown>
): Promise<ResearchSession> {
  const response = await fetch(`${API_URL}/research/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, context }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to create session: ${response.statusText}`,
      response.status,
      error.detail
    );
  }

  const data = await response.json();
  return mapSessionFromApi(data);
}

/**
 * Get a session by ID.
 *
 * @param sessionId - The session ID
 * @returns The session if found
 */
export async function getSession(sessionId: string): Promise<ResearchSession> {
  const response = await fetch(`${API_URL}/research/sessions/${sessionId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to get session: ${response.statusText}`,
      response.status,
      error.detail
    );
  }

  const data = await response.json();
  return mapSessionFromApi(data);
}

/**
 * Start a research session and return an EventSource for SSE streaming.
 *
 * @param sessionId - The session ID to start
 * @param onEvent - Callback for each SSE event
 * @param onError - Callback for errors
 * @param onComplete - Callback when stream ends
 * @returns Cleanup function to close the connection
 */
export function startSession(
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void
): () => void {
  const url = `${API_URL}/research/sessions/${sessionId}/start`;
  const eventSource = new EventSource(url);
  
  // Track if we've received a terminal event (workflow_completed or workflow_failed)
  let workflowEnded = false;

  // SSE event types - both trace-based (primary) and legacy (backward compat)
  const eventTypes = [
    // Trace-based events (primary - handled by frontend)
    'workflow_started',
    'workflow_completed',
    'workflow_failed',
    'trace_span_started',
    'trace_span_completed',
    'trace_tool_call',
    'heartbeat',
    'error',
    // Subagent events (from stream_callback - may not fire for hosted agents)
    'subagent_tool_started',
    'subagent_tool_completed',
    'subagent_progress',
    // Legacy events (emitted by backend, converted to activities)
    'session_started',
    'agent_started',
    'agent_progress',
    'agent_completed',
    'agent_response',
    'tool_call_started',
    'tool_call_completed',
    'scratchpad_updated',
    'synthesis_completed',
  ];

  console.log(`[SSE] Connecting to: ${url}`);
  console.log(`[SSE] Registered event types: ${eventTypes.join(', ')}`);
  
  eventTypes.forEach((eventType) => {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      console.log(`[SSE] RAW EVENT received: type=${eventType}, data.length=${e.data?.length}`);
      console.log(`[SSE] RAW DATA: ${e.data?.substring(0, 500)}...`);
      
      // Handle the 'error' event type specially - it may have undefined data
      // when the server closes the connection after workflow_failed
      if (eventType === 'error') {
        if (!e.data) {
          console.log('[SSE] Error event with no data - likely server connection closed after workflow ended');
          return; // Ignore error events with no data
        }
      }
      
      try {
        const data = JSON.parse(e.data);
        console.log(`[SSE] PARSED EVENT: type=${eventType}`, data);
        
        // Check for terminal events
        if (eventType === 'workflow_completed' || eventType === 'workflow_failed') {
          console.log(`[SSE] Terminal event received: ${eventType}`);
          workflowEnded = true;
        }
        
        onEvent(data as SSEEvent);
      } catch (err) {
        console.error(`[SSE] Failed to parse event ${eventType}:`, err);
        console.error(`[SSE] Raw data was:`, e.data);
      }
    });
  });

  // Handle generic message events (fallback)
  eventSource.onmessage = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data as SSEEvent);
    } catch (err) {
      console.error('Failed to parse SSE message:', err);
    }
  };

  // Handle connection errors
  eventSource.onerror = () => {
    // If workflow already ended, this is expected (server closed connection)
    if (workflowEnded) {
      eventSource.close();
      onComplete();
      return;
    }
    
    // Check if stream ended (readyState === CLOSED means server closed it)
    if (eventSource.readyState === EventSource.CLOSED) {
      // Server closed connection - could be normal end or error
      // Don't report as error, just complete
      onComplete();
    } else {
      // Actual connection error (network issue, etc.)
      onError(new Error('SSE connection error'));
      eventSource.close();
    }
  };

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}

/**
 * Answer a question in a session.
 *
 * @param sessionId - The session ID
 * @param questionId - The question ID
 * @param answer - The user's answer
 */
export async function answerQuestion(
  sessionId: string,
  questionId: string,
  answer: string
): Promise<void> {
  const response = await fetch(
    `${API_URL}/research/sessions/${sessionId}/questions/${questionId}/answer`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ answer }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to answer question: ${response.statusText}`,
      response.status,
      error.detail
    );
  }
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// === Scratchpad Polling API ===

/**
 * Plan data from scratchpad.
 */
export interface PlanData {
  session_id: string;
  tasks: Array<{
    task_id: string;
    description: string;
    priority?: 'low' | 'medium' | 'high';
    assigned_to?: string;
    status: 'todo' | 'in-progress' | 'done' | 'blocked';
    created_at?: string;
    updated_at?: string;
  }>;
  total_tasks: number;
  tasks_by_status: {
    todo: number;
    'in-progress': number;
    done: number;
    blocked: number;
  };
}

/**
 * Notes data from scratchpad.
 */
export interface NotesData {
  session_id: string;
  notes: Array<{
    note_id?: string;
    id?: string;
    content: string;
    author: string;
    section?: string;
    source_url?: string;
    created_at?: string;
    timestamp?: string;
  }>;
  total_notes: number;
  notes_by_author: Record<string, number>;
}

/**
 * Draft data from scratchpad.
 */
export interface DraftData {
  session_id: string;
  sections: Array<{
    section_id: string;
    title: string;
    content: string;
    author: string;
    order?: number;
    created_at?: string;
    updated_at?: string;
  }>;
  total_sections: number;
}

/**
 * Get the current research plan with all tasks.
 *
 * @param sessionId - The session ID
 * @returns The plan data with tasks
 */
export async function getPlan(sessionId: string): Promise<PlanData> {
  const response = await fetch(
    `${API_URL}/research/sessions/${sessionId}/scratchpad/plan`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to get plan: ${response.statusText}`,
      response.status,
      error.detail
    );
  }

  return response.json();
}

/**
 * Get all research notes.
 *
 * @param sessionId - The session ID
 * @returns The notes data
 */
export async function getNotes(sessionId: string): Promise<NotesData> {
  const response = await fetch(
    `${API_URL}/research/sessions/${sessionId}/scratchpad/notes`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to get notes: ${response.statusText}`,
      response.status,
      error.detail
    );
  }

  return response.json();
}

/**
 * Get current draft sections.
 *
 * @param sessionId - The session ID
 * @returns The draft data
 */
export async function getDraft(sessionId: string): Promise<DraftData> {
  const response = await fetch(
    `${API_URL}/research/sessions/${sessionId}/scratchpad/draft`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      `Failed to get draft: ${response.statusText}`,
      response.status,
      error.detail
    );
  }

  return response.json();
}

/**
 * Poll all scratchpad data at once.
 *
 * @param sessionId - The session ID
 * @returns Object with plan, notes, and draft data
 */
export async function pollScratchpad(sessionId: string): Promise<{
  plan: PlanData | null;
  notes: NotesData | null;
  draft: DraftData | null;
}> {
  const [planResult, notesResult, draftResult] = await Promise.allSettled([
    getPlan(sessionId),
    getNotes(sessionId),
    getDraft(sessionId),
  ]);

  return {
    plan: planResult.status === 'fulfilled' ? planResult.value : null,
    notes: notesResult.status === 'fulfilled' ? notesResult.value : null,
    draft: draftResult.status === 'fulfilled' ? draftResult.value : null,
  };
}

/**
 * Map API session response to frontend type.
 */
function mapSessionFromApi(data: Record<string, unknown>): ResearchSession {
  return {
    sessionId: data.session_id as string,
    query: data.query as string,
    status: data.status as ResearchSession['status'],
    createdAt: data.created_at as string,
    startedAt: data.started_at as string | undefined,
    completedAt: data.completed_at as string | undefined,
  };
}
