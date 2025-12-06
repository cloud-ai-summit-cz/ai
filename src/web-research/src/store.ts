/**
 * Zustand store for application state management.
 *
 * ADR-007: UI events are generated directly by the orchestrator middleware,
 * providing real-time updates. OpenTelemetry traces still flow to App Insights
 * for observability, but are not used for UI events.
 */

import { create } from 'zustand';
import type {
  ResearchSession,
  Task,
  TaskStatus,
  Note,
  DraftSection,
  Question,
  Activity,
  ActivityType,
  ScratchpadState,
  SessionStatus,
  SSEEvent,
  SSEEventType,
  TraceSpanStartedData,
  TraceSpanCompletedData,
  TraceToolCallData,
  WorkflowStartedData,
  WorkflowCompletedData,
  WorkflowFailedData,
  DemoStateSnapshot,
} from './types';
import { createSession, startSession, pollScratchpad } from './api';

interface ResearchStore {
  // === Session State ===
  session: ResearchSession | null;
  setSession: (session: ResearchSession | null) => void;
  updateSessionStatus: (status: SessionStatus) => void;

  // === Scratchpad State ===
  scratchpad: ScratchpadState;

  // Plan actions
  setTasks: (tasks: Task[]) => void;

  // Notes actions
  setNotes: (notes: Note[]) => void;

  // Draft actions
  setDraftSections: (sections: DraftSection[]) => void;

  // Questions actions
  setQuestions: (questions: Question[]) => void;
  addQuestion: (question: Question) => void;
  answerQuestion: (questionId: string, answer: string) => void;

  // === Activity State (replaces chat messages) ===
  activities: Activity[];
  addActivity: (activity: Activity) => void;
  clearActivities: () => void;

  // === Final Report State ===
  finalReport: string | null;
  setFinalReport: (report: string | null) => void;

  // === UI State ===
  isConnected: boolean;
  setConnected: (connected: boolean) => void;
  activePanel: 'activity' | 'plan' | 'notes' | 'draft' | 'final';
  setActivePanel: (panel: 'activity' | 'plan' | 'notes' | 'draft' | 'final') => void;
  showQuestionModal: boolean;
  setShowQuestionModal: (show: boolean) => void;

  // === Demo Mode ===
  isDemoMode: boolean;
  exportDemoState: () => DemoStateSnapshot | null;
  loadDemoState: (snapshot: DemoStateSnapshot) => void;

  // === SSE & Workflow ===
  sseCleanup: (() => void) | null;
  pollingInterval: ReturnType<typeof setInterval> | null;
  startResearchSession: (query: string, language?: 'cs' | 'en') => Promise<void>;
  handleSSEEvent: (event: SSEEvent) => void;
  pollScratchpadState: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  resetState: () => void;
}

const initialScratchpad: ScratchpadState = {
  plan: [],
  notes: [],
  draft: [],
  questions: [],
};

export const useResearchStore = create<ResearchStore>((set, get) => ({
  // === Session State ===
  session: null,
  setSession: (session) => set({ session }),
  updateSessionStatus: (status) =>
    set((state) => ({
      session: state.session ? { ...state.session, status } : null,
    })),

  // === Scratchpad State ===
  scratchpad: initialScratchpad,

  setTasks: (tasks) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, plan: tasks },
    })),

  setNotes: (notes) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, notes },
    })),

  setDraftSections: (sections) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, draft: sections },
    })),

  setQuestions: (questions) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, questions },
    })),

  addQuestion: (question) => {
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        questions: [...state.scratchpad.questions, question],
      },
      showQuestionModal: question.priority === 'blocking' || state.showQuestionModal,
    }));
  },

  answerQuestion: (questionId, answer) => {
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        questions: state.scratchpad.questions.map((q) =>
          q.id === questionId
            ? { ...q, answer, answered: true, answered_at: new Date().toISOString() }
            : q
        ),
      },
    }));
  },

  // === Activity State ===
  activities: [],
  addActivity: (activity) => {
    console.debug('[STORE] Activity:', activity.type, activity.action?.slice(0, 50));
    set((state) => ({
      activities: [...state.activities, activity],
    }));
  },
  clearActivities: () => set({ activities: [] }),

  // === Final Report State ===
  finalReport: null,
  setFinalReport: (report) => set({ finalReport: report }),

  // === UI State ===
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),
  activePanel: 'activity',
  setActivePanel: (panel) => {
    set({ activePanel: panel });
    if (panel !== 'activity') {
      get().pollScratchpadState().catch((err) => {
        console.debug('Failed to refresh scratchpad on tab switch:', err);
      });
    }
  },
  showQuestionModal: false,
  setShowQuestionModal: (show) => set({ showQuestionModal: show }),

  // === Demo Mode ===
  isDemoMode: false,

  exportDemoState: () => {
    const state = get();
    if (!state.session) {
      console.warn('Cannot export demo state: no active session');
      return null;
    }
    
    const snapshot: DemoStateSnapshot = {
      version: 1,
      exportedAt: new Date().toISOString(),
      session: { 
        ...state.session, 
        // Mark as completed in the export so it doesn't try to reconnect
        status: state.session.status === 'running' || state.session.status === 'preparing' 
          ? 'completed' 
          : state.session.status 
      },
      scratchpad: state.scratchpad,
      activities: state.activities,
      finalReport: state.finalReport,
    };
    
    return snapshot;
  },

  loadDemoState: (snapshot: DemoStateSnapshot) => {
    const store = get();
    
    // Clean up any existing connections
    if (store.sseCleanup) {
      store.sseCleanup();
    }
    store.stopPolling();
    
    // Load the snapshot state
    set({
      session: snapshot.session,
      scratchpad: snapshot.scratchpad,
      activities: snapshot.activities,
      finalReport: snapshot.finalReport,
      isDemoMode: true,
      isConnected: false,
      activePanel: 'activity',
      showQuestionModal: false,
      sseCleanup: null,
      pollingInterval: null,
    });
    
    console.info('Demo state loaded successfully');
  },

  // === SSE & Workflow ===
  sseCleanup: null,
  pollingInterval: null,

  startPolling: () => {
    const store = get();
    if (store.pollingInterval) {
      clearInterval(store.pollingInterval);
    }
    
    const interval = setInterval(() => {
      const currentStore = get();
      if (currentStore.session?.status === 'running') {
        currentStore.pollScratchpadState().catch((err) => {
          console.debug('Background poll failed:', err);
        });
      } else {
        currentStore.stopPolling();
      }
    }, 5000);
    
    set({ pollingInterval: interval });
    console.debug('Started background scratchpad polling (5s interval)');
  },

  stopPolling: () => {
    const store = get();
    if (store.pollingInterval) {
      clearInterval(store.pollingInterval);
      set({ pollingInterval: null });
      console.debug('Stopped background scratchpad polling');
    }
  },

  startResearchSession: async (query: string, language: 'cs' | 'en' = 'cs') => {
    const store = get();

    if (store.sseCleanup) {
      store.sseCleanup();
    }
    store.stopPolling();

    set({
      scratchpad: initialScratchpad,
      activities: [],
      isConnected: false,
    });

    try {
      const session = await createSession(query, language);
      set({ session });

      // Add initial activity
      store.addActivity({
        id: `activity-${Date.now()}`,
        type: 'system',
        timestamp: new Date().toISOString(),
        actor: 'System',
        action: `Research session started for: "${query}"`,
      });

      // Start SSE streaming
      const cleanup = startSession(
        session.sessionId,
        (event) => get().handleSSEEvent(event),
        (error) => {
          console.error('SSE error:', error);
          set({ isConnected: false });
          get().addActivity({
            id: `activity-${Date.now()}`,
            type: 'workflow_error',
            timestamp: new Date().toISOString(),
            actor: 'System',
            action: `Connection error: ${error.message}`,
            success: false,
          });
        },
        () => {
          set({ isConnected: false });
        }
      );

      set({ sseCleanup: cleanup, isConnected: true });
      store.startPolling();
    } catch (error) {
      console.error('Failed to start research session:', error);
      store.addActivity({
        id: `activity-${Date.now()}`,
        type: 'workflow_error',
        timestamp: new Date().toISOString(),
        actor: 'System',
        action: `Failed to start session: ${error instanceof Error ? error.message : 'Unknown error'}`,
        success: false,
      });
    }
  },

  handleSSEEvent: (event: SSEEvent) => {
    const store = get();
    const eventType = event.event_type as SSEEventType;
    const data = event.data as Record<string, unknown>;
    const timestamp = event.timestamp || new Date().toISOString();
    
    // Concise logging - just event type and key identifiers
    const logSummary: Record<string, unknown> = { type: eventType };
    if (data.section_name) logSummary.section = data.section_name;
    if (data.operation) logSummary.op = data.operation;
    if (data.tasks_created) logSummary.tasks = data.tasks_created;
    if (data.span_name) logSummary.span = data.span_name;
    console.debug('[STORE] SSE:', logSummary);

    switch (eventType) {
      // === Workflow Lifecycle ===
      case 'workflow_started': {
        // Handle both nested data.operation_id and direct data field
        const workflowData = (data.data ? data.data : data) as unknown as WorkflowStartedData;
        // Set to 'preparing' initially - will change to 'running' when orchestration starts
        set((state) => ({
          session: state.session 
            ? { ...state.session, operationId: workflowData.operation_id, status: 'preparing' }
            : null,
        }));
        store.addActivity({
          id: `activity-${Date.now()}`,
          type: 'workflow_start',
          timestamp,
          actor: 'Orchestrator',
          action: 'Research workflow initialized',
          operationId: workflowData.operation_id,
          details: workflowData.trace_polling_enabled 
            ? 'Trace polling enabled' 
            : 'Trace polling disabled',
        });
        break;
      }

      case 'workflow_completed': {
        const completedData = data as unknown as WorkflowCompletedData;
        store.updateSessionStatus('completed');
        store.stopPolling();
        store.pollScratchpadState().catch(() => {});
        store.addActivity({
          id: `activity-${Date.now()}`,
          type: 'workflow_complete',
          timestamp,
          actor: 'Orchestrator',
          action: 'Research workflow completed',
          durationMs: completedData.total_time_ms,
          success: true,
          details: completedData.total_tool_calls 
            ? `${completedData.total_tool_calls} tool calls` 
            : undefined,
        });
        break;
      }

      case 'workflow_failed': {
        const failedData = data as unknown as WorkflowFailedData;
        store.updateSessionStatus('failed');
        store.stopPolling();
        store.addActivity({
          id: `activity-${Date.now()}`,
          type: 'workflow_error',
          timestamp,
          actor: 'System',
          action: `Workflow failed: ${failedData.error}`,
          success: false,
          details: failedData.error_type,
        });
        break;
      }

      // === Trace Events (primary source) ===
      case 'trace_span_started': {
        const spanData = data as unknown as TraceSpanStartedData;
        const activity = parseTraceSpanStarted(spanData, timestamp);
        if (activity) {
          store.addActivity(activity);
        }
        break;
      }

      case 'trace_span_completed': {
        const spanData = data as unknown as TraceSpanCompletedData;
        const activity = parseTraceSpanCompleted(spanData, timestamp);
        if (activity) {
          store.addActivity(activity);
          // Poll scratchpad after agent completes
          if (activity.type === 'agent_complete') {
            store.pollScratchpadState().catch(() => {});
          }
        }
        break;
      }

      case 'trace_tool_call': {
        const toolData = data as unknown as TraceToolCallData;
        const activity = parseTraceToolCall(toolData, timestamp);
        if (activity) {
          store.addActivity(activity);
          // Poll scratchpad after scratchpad tools
          if (isScratchpadTool(toolData.tool_name)) {
            store.pollScratchpadState().catch(() => {});
          }
        }
        break;
      }

      // === Keep-Alive ===
      case 'heartbeat':
        console.debug('SSE heartbeat received');
        break;

      // === Error ===
      case 'error':
        store.addActivity({
          id: `activity-${Date.now()}`,
          type: 'workflow_error',
          timestamp,
          actor: 'System',
          action: (data.error as string) || 'Unknown error',
          success: false,
        });
        break;

      // === Legacy Events (convert to activities as fallback) ===
      // These are emitted directly by the orchestrator.
      // We convert them to activities for display.
      case 'session_started':
        // Already handled by workflow_started, skip
        console.debug('Legacy session_started event (skipped - handled by workflow_started)');
        break;

      case 'agent_started': {
        const agentData = data as { phase?: string; description?: string; agent_name?: string };
        // Transition from 'preparing' to 'running' when orchestration phase begins
        if (agentData.phase === 'orchestration') {
          store.updateSessionStatus('running');
        }
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'agent_working',
          timestamp,
          actor: formatAgentName(agentData.agent_name) || 'Orchestrator',
          action: agentData.description || 'Agent started',
          details: agentData.phase,
          agentColor: getAgentColor(agentData.agent_name),
        });
        break;
      }

      case 'agent_progress': {
        const progressData = data as { message?: string; agent_name?: string };
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'agent_working',
          timestamp,
          actor: formatAgentName(progressData.agent_name),
          action: progressData.message || 'Processing...',
          agentColor: getAgentColor(progressData.agent_name),
        });
        break;
      }

      case 'agent_completed': {
        const completedData = data as { agent_name?: string; summary?: string };
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'agent_complete',
          timestamp,
          actor: formatAgentName(completedData.agent_name),
          action: completedData.summary || 'Analysis complete',
          success: true,
          agentColor: getAgentColor(completedData.agent_name),
        });
        store.pollScratchpadState().catch(() => {});
        break;
      }

      case 'agent_response': {
        const responseData = data as { agent_name?: string; response?: string; response_preview?: string; execution_time_ms?: number };
        const preview = responseData.response_preview || responseData.response;
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'agent_complete',
          timestamp,
          actor: formatAgentName(responseData.agent_name),
          action: 'Response received',
          success: true,
          durationMs: responseData.execution_time_ms,
          preview: preview,  // Store full text, truncation handled in UI
          agentColor: getAgentColor(responseData.agent_name),
        });
        break;
      }

      case 'tool_call_started': {
        const toolData = data as { tool_name?: string; agent_name?: string; input_args?: Record<string, unknown> };
        const toolAction = getToolAction(toolData.tool_name || 'unknown');
        // Extract a preview from input_args
        const inputPreview = extractInputPreview(toolData.input_args);
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: toolAction.type,
          timestamp,
          actor: formatAgentName(toolData.agent_name),
          action: `${toolAction.icon} ${toolAction.action}`,
          target: toolData.tool_name,
          preview: inputPreview,
          agentColor: getAgentColor(toolData.agent_name),
        });
        break;
      }

      case 'tool_call_completed': {
        const toolData = data as { 
          tool_name?: string; 
          agent_name?: string; 
          execution_time_ms?: number;
          output?: string | Array<{ type: string; text: string }>;
        };
        const toolAction = getToolAction(toolData.tool_name || 'unknown');
        const durationSec = toolData.execution_time_ms 
          ? (toolData.execution_time_ms / 1000).toFixed(1) 
          : '?';
        // Extract output preview
        const outputPreview = extractOutputPreview(toolData.output);
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: toolAction.type,
          timestamp,
          actor: formatAgentName(toolData.agent_name),
          action: `${toolAction.icon} ${toolAction.action} ✓ (${durationSec}s)`,
          target: toolData.tool_name,
          durationMs: toolData.execution_time_ms,
          success: true,
          preview: outputPreview,
          agentColor: getAgentColor(toolData.agent_name),
        });
        // Poll scratchpad after tool calls
        if (isScratchpadTool(toolData.tool_name || '')) {
          store.pollScratchpadState().catch(() => {});
        }
        break;
      }

      case 'scratchpad_updated': {
        const scratchData = data as { 
          section_name?: string; 
          operation?: string; 
          updated_by?: string;
          tool_type?: string;
          tasks_created?: number;
          content_preview?: string;
        };
        const section = scratchData.section_name || 'scratchpad';
        const operation = scratchData.operation || 'updated';
        let action = `📋 ${section} ${operation}`;
        if (scratchData.tasks_created) {
          action = `📋 Created ${scratchData.tasks_created} tasks`;
        }
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'scratchpad_update',
          timestamp,
          actor: formatAgentName(scratchData.updated_by),
          action,
          details: scratchData.tool_type,
          preview: scratchData.content_preview,  // Store full text, truncation handled in UI
          agentColor: getAgentColor(scratchData.updated_by),
        });
        store.pollScratchpadState().catch(() => {});
        break;
      }

      case 'synthesis_completed': {
        const synthData = data as { summary?: string; synthesis?: string };
        // Store the full synthesis for the Final Report tab
        if (synthData.synthesis) {
          store.setFinalReport(synthData.synthesis);
          // Auto-navigate to Final tab when synthesis is ready
          store.setActivePanel('final');
        }
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'workflow_complete',
          timestamp,
          actor: 'Synthesizer',
          action: 'Final report ready',
          success: true,
          agentColor: getAgentColor('synthesizer'),
        });
        store.pollScratchpadState().catch(() => {});
        break;
      }

      // === Subagent streaming events (from MAF stream_callback) ===
      case 'subagent_tool_started': {
        const subagentData = data as { 
          subagent_name?: string; 
          tool_name?: string; 
          tool_call_id?: string;
          input_preview?: string;
        };
        const toolAction = getToolAction(subagentData.tool_name || 'unknown');
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: toolAction.type,
          timestamp,
          actor: formatAgentName(subagentData.subagent_name),
          action: `${toolAction.icon} ${toolAction.action}`,
          target: subagentData.tool_name,
          preview: subagentData.input_preview,
          agentColor: getAgentColor(subagentData.subagent_name),
        });
        break;
      }

      case 'subagent_tool_completed': {
        const subagentData = data as { 
          subagent_name?: string; 
          tool_name?: string; 
          tool_call_id?: string;
          output_preview?: string;
        };
        const toolAction = getToolAction(subagentData.tool_name || 'unknown');
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: toolAction.type,
          timestamp,
          actor: formatAgentName(subagentData.subagent_name),
          action: `${toolAction.icon} ${toolAction.action} ✓`,
          target: subagentData.tool_name,
          success: true,
          preview: subagentData.output_preview,
          agentColor: getAgentColor(subagentData.subagent_name),
        });
        // Poll scratchpad after subagent tool calls
        if (isScratchpadTool(subagentData.tool_name || '')) {
          store.pollScratchpadState().catch(() => {});
        }
        break;
      }

      case 'subagent_progress': {
        const subagentData = data as { 
          subagent_name?: string; 
          text_chunk?: string;
        };
        // Only emit for substantial chunks to avoid spam
        if (subagentData.text_chunk && subagentData.text_chunk.length >= 50) {
          store.addActivity({
            id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            type: 'agent_working',
            timestamp,
            actor: formatAgentName(subagentData.subagent_name),
            action: 'Processing...',
            preview: subagentData.text_chunk?.substring(0, 150),
            agentColor: getAgentColor(subagentData.subagent_name),
          });
        }
        break;
      }

      // === Question/HITL events ===
      case 'question_added': {
        const questionData = data as {
          question_id: string;
          question: string;
          context?: string;
          asked_by?: string;
          priority?: 'low' | 'medium' | 'high' | 'blocking';
          timestamp?: string;
        };
        const newQuestion = {
          id: questionData.question_id,
          question: questionData.question,
          context: questionData.context,
          asked_by: questionData.asked_by || 'Agent',
          priority: questionData.priority || 'medium',
          asked_at: questionData.timestamp || timestamp,
          answered: false,
        };
        store.addQuestion(newQuestion);
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'system',
          timestamp,
          actor: formatAgentName(questionData.asked_by),
          action: `❓ Asked: ${questionData.question.substring(0, 80)}${questionData.question.length > 80 ? '...' : ''}`,
          preview: questionData.context,
          agentColor: getAgentColor(questionData.asked_by),
        });
        break;
      }

      case 'awaiting_user_input': {
        const awaitingData = data as {
          reason?: string;
          blocking_question_ids?: string[];
          pending_question_count?: number;
        };
        store.setShowQuestionModal(true);
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'system',
          timestamp,
          actor: 'System',
          action: `⏸️ Workflow paused - awaiting user input`,
          preview: awaitingData.reason || `${awaitingData.pending_question_count || 0} question(s) need your response`,
        });
        break;
      }

      case 'questions_answered': {
        const answeredData = data as {
          answered_question_ids?: string[];
          answer_count?: number;
        };
        store.addActivity({
          id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          type: 'system',
          timestamp,
          actor: 'User',
          action: `✅ Answered ${answeredData.answer_count || answeredData.answered_question_ids?.length || 0} question(s)`,
          success: true,
        });
        // Refresh questions from server to get updated state
        store.pollScratchpadState().catch(() => {});
        break;
      }

      default:
        console.debug(`Unknown SSE event type: ${eventType}`);
    }
  },

  pollScratchpadState: async () => {
    const store = get();
    const session = store.session;
    
    if (!session) {
      return;
    }

    try {
      // Note: We intentionally don't poll questions here to avoid race conditions
      // with optimistic updates when users are answering questions.
      // Questions are updated via SSE events (question_added) and optimistic local updates.
      const { plan, notes, draft } = await pollScratchpad(session.sessionId);

      if (plan && plan.tasks.length > 0) {
        const tasks: Task[] = plan.tasks.map((t, idx) => ({
          id: t.task_id || `task-${idx}-${Date.now()}`,
          description: t.description,
          status: t.status as TaskStatus,
          assignedTo: t.assigned_to,
          createdAt: t.created_at || new Date().toISOString(),
        }));
        set((state) => ({
          scratchpad: { ...state.scratchpad, plan: tasks },
        }));
      }

      if (notes && notes.notes.length > 0) {
        const notesList: Note[] = notes.notes.map((n) => ({
          id: n.note_id || n.id || `note-${Date.now()}`,
          content: n.content,
          author: n.author,
          timestamp: n.created_at || n.timestamp || new Date().toISOString(),
          tags: [],
          sourceUrl: n.source_url,
        }));
        set((state) => ({
          scratchpad: { ...state.scratchpad, notes: notesList },
        }));
      }

      if (draft && draft.sections.length > 0) {
        const draftSections: DraftSection[] = draft.sections.map((s) => ({
          id: s.section_id,
          title: s.title,
          content: s.content,
          lastUpdatedBy: s.author,
          lastUpdatedAt: s.updated_at || s.created_at,
          version: 1,
        }));
        set((state) => ({
          scratchpad: { ...state.scratchpad, draft: draftSections },
        }));
      }
    } catch (error) {
      console.debug('Scratchpad poll error:', error);
    }
  },

  resetState: () => {
    const store = get();
    if (store.sseCleanup) {
      store.sseCleanup();
    }
    store.stopPolling();
    set({
      session: null,
      scratchpad: initialScratchpad,
      activities: [],
      finalReport: null,
      isDemoMode: false,
      isConnected: false,
      activePanel: 'activity',
      showQuestionModal: false,
      sseCleanup: null,
      pollingInterval: null,
    });
  },
}));

// === Helper Functions ===

/**
 * Format agent name for display.
 */
function formatAgentName(agentName: string | undefined): string {
  if (!agentName) return 'Agent';
  return agentName
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Get a consistent color for an agent based on its name.
 * This ensures the same agent always gets the same color.
 */
function getAgentColor(agentName: string | undefined): string | undefined {
  if (!agentName) return undefined;
  
  const agentColors: Record<string, string> = {
    'orchestrator': 'blue',
    'research-orchestrator': 'blue',
    'market-analyst': 'purple',
    'market_analyst': 'purple',
    'competitor-analyst': 'orange',
    'competitor_analyst': 'orange',
    'location-scout': 'cyan',
    'location_scout': 'cyan',
    'finance-analyst': 'green',
    'finance_analyst': 'green',
    'synthesizer': 'pink',
  };
  
  const lowerName = agentName.toLowerCase();
  for (const [key, color] of Object.entries(agentColors)) {
    if (lowerName.includes(key)) {
      return color;
    }
  }
  
  // Default: hash the agent name to get consistent color
  const colors = ['blue', 'purple', 'cyan', 'orange', 'pink', 'yellow', 'green'];
  const hash = lowerName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

/**
 * Check if a tool is a scratchpad tool that updates state.
 */
function isScratchpadTool(toolName: string): boolean {
  const scratchpadTools = [
    'add_note', 'add_notes',
    'add_task', 'add_tasks',
    'update_task',
    'write_draft_section',
    'read_plan', 'read_notes', 'read_draft',
  ];
  return scratchpadTools.some(t => toolName.toLowerCase().includes(t.toLowerCase()));
}

/**
 * Extract a preview string from tool input arguments.
 */
function extractInputPreview(inputArgs: Record<string, unknown> | undefined): string | undefined {
  if (!inputArgs) return undefined;
  
  // Common field names that might contain useful preview text
  const previewFields = ['query', 'search_query', 'content', 'text', 'note', 'description', 'task'];
  for (const field of previewFields) {
    const value = inputArgs[field];
    if (typeof value === 'string' && value.length > 0) {
      return value.substring(0, 100) + (value.length > 100 ? '...' : '');
    }
  }
  
  // Try to stringify first non-empty string value
  for (const value of Object.values(inputArgs)) {
    if (typeof value === 'string' && value.length > 0) {
      return value;  // Return full text, truncation handled in UI
    }
  }
  
  return undefined;
}

/**
 * Extract a preview string from tool output.
 * Returns full text - truncation is handled in the UI component.
 */
function extractOutputPreview(output: string | Array<{ type: string; text: string }> | unknown): string | undefined {
  if (!output) return undefined;
  
  // Handle array format (common in Azure AI Agent Service)
  if (Array.isArray(output)) {
    const textItem = output.find((item: unknown) => 
      typeof item === 'object' && item !== null && 'text' in item
    ) as { text?: string } | undefined;
    if (textItem?.text) {
      return textItem.text;  // Return full text
    }
  }
  
  // Handle string output
  if (typeof output === 'string') {
    return output;  // Return full text
  }
  
  // Try to extract from object with common fields
  if (typeof output === 'object' && output !== null) {
    const obj = output as Record<string, unknown>;
    const previewFields = ['result', 'content', 'text', 'summary', 'message'];
    for (const field of previewFields) {
      const value = obj[field];
      if (typeof value === 'string' && value.length > 0) {
        return value;  // Return full text
      }
    }
  }
  
  return undefined;
}

/**
 * Get action info for a tool call (used by legacy event handlers).
 */
function getToolAction(toolName: string): { action: string; icon: string; type: ActivityType } {
  const toolActions: Record<string, { action: string; icon: string; type: ActivityType }> = {
    'add_note': { action: 'Adding research note', icon: '📝', type: 'scratchpad_update' },
    'add_notes': { action: 'Adding research notes', icon: '📝', type: 'scratchpad_update' },
    'add_task': { action: 'Adding task to plan', icon: '📋', type: 'scratchpad_update' },
    'add_tasks': { action: 'Adding tasks to plan', icon: '📋', type: 'scratchpad_update' },
    'update_task': { action: 'Updating task status', icon: '✅', type: 'scratchpad_update' },
    'write_draft_section': { action: 'Writing draft section', icon: '📄', type: 'scratchpad_update' },
    'read_plan': { action: 'Reading research plan', icon: '📋', type: 'tool_call' },
    'read_notes': { action: 'Reading research notes', icon: '📝', type: 'tool_call' },
    'read_draft': { action: 'Reading draft', icon: '📄', type: 'tool_call' },
    'web_search': { action: 'Searching the web', icon: '🔍', type: 'tool_call' },
    'tavily_search': { action: 'Searching the web', icon: '🔍', type: 'tool_call' },
    'market_analysis': { action: 'Running market analysis', icon: '📊', type: 'agent_delegation' },
    'competitor_analysis': { action: 'Running competitor analysis', icon: '🏢', type: 'agent_delegation' },
    'synthesize_findings': { action: 'Synthesizing findings', icon: '📑', type: 'agent_delegation' },
  };

  // Find matching tool action
  const lowerName = toolName.toLowerCase();
  for (const [key, value] of Object.entries(toolActions)) {
    if (lowerName.includes(key.toLowerCase())) {
      return value;
    }
  }
  
  // Default for unknown tools
  return { action: `Calling ${toolName}`, icon: '🔧', type: 'tool_call' };
}

/**
 * Parse trace_span_started event into an Activity.
 */
function parseTraceSpanStarted(
  data: TraceSpanStartedData,
  timestamp: string
): Activity | null {
  const spanName = data.span_name;
  const agentName = data.agent_name;

  // Skip internal spans
  if (spanName.includes('heartbeat') || spanName.includes('health')) {
    return null;
  }

  // Agent delegation patterns
  if (spanName.startsWith('delegate_to_')) {
    const targetAgent = spanName.replace('delegate_to_', '');
    return {
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent_delegation',
      timestamp,
      actor: 'Orchestrator',
      action: `Delegating to ${formatAgentName(targetAgent)}`,
      target: targetAgent,
      operationId: data.operation_id,
    };
  }

  // Agent working pattern
  if (spanName.startsWith('agent.')) {
    const agent = spanName.replace('agent.', '');
    return {
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent_working',
      timestamp,
      actor: formatAgentName(agent),
      action: 'Starting analysis...',
      operationId: data.operation_id,
    };
  }

  // Generic span - only show if it has agent context
  if (agentName) {
    return {
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent_working',
      timestamp,
      actor: formatAgentName(agentName),
      action: spanName,
      operationId: data.operation_id,
    };
  }

  return null;
}

/**
 * Parse trace_span_completed event into an Activity.
 */
function parseTraceSpanCompleted(
  data: TraceSpanCompletedData,
  timestamp: string
): Activity | null {
  const spanName = data.span_name;
  const agentName = data.agent_name;

  // Skip internal spans
  if (spanName.includes('heartbeat') || spanName.includes('health')) {
    return null;
  }

  // Agent completion patterns
  if (spanName.startsWith('delegate_to_') || spanName.startsWith('agent.')) {
    const agent = spanName.replace('delegate_to_', '').replace('agent.', '');
    return {
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent_complete',
      timestamp,
      actor: formatAgentName(agent),
      action: 'Analysis complete',
      durationMs: data.duration_ms,
      success: data.success !== false,
      operationId: data.operation_id,
    };
  }

  // Generic completion with agent context
  if (agentName) {
    return {
      id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: 'agent_complete',
      timestamp,
      actor: formatAgentName(agentName),
      action: `Completed: ${spanName}`,
      durationMs: data.duration_ms,
      success: data.success !== false,
      operationId: data.operation_id,
    };
  }

  return null;
}

/**
 * Parse trace_tool_call event into an Activity.
 */
function parseTraceToolCall(
  data: TraceToolCallData,
  timestamp: string
): Activity | null {
  const toolName = data.tool_name;
  const agentName = data.agent_name;

  // Map tool names to user-friendly actions
  const toolActions: Record<string, { action: string; type: ActivityType }> = {
    'add_note': { action: '📝 Adding research note', type: 'scratchpad_update' },
    'add_notes': { action: '📝 Adding research notes', type: 'scratchpad_update' },
    'add_task': { action: '📋 Adding task to plan', type: 'scratchpad_update' },
    'add_tasks': { action: '📋 Adding tasks to plan', type: 'scratchpad_update' },
    'update_task': { action: '✅ Updating task status', type: 'scratchpad_update' },
    'write_draft_section': { action: '📄 Writing draft section', type: 'scratchpad_update' },
    'read_plan': { action: '📋 Reading research plan', type: 'tool_call' },
    'read_notes': { action: '📝 Reading research notes', type: 'tool_call' },
    'read_draft': { action: '📄 Reading draft', type: 'tool_call' },
    'web_search': { action: '🔍 Searching the web', type: 'tool_call' },
    'tavily_search': { action: '🔍 Searching the web', type: 'tool_call' },
  };

  // Find matching tool action
  let activityInfo = toolActions[toolName.toLowerCase()];
  
  // Fallback for unknown tools
  if (!activityInfo) {
    // Check for partial matches
    for (const [key, value] of Object.entries(toolActions)) {
      if (toolName.toLowerCase().includes(key)) {
        activityInfo = value;
        break;
      }
    }
  }
  
  // Default for unknown tools
  if (!activityInfo) {
    activityInfo = { action: `Calling ${toolName}`, type: 'tool_call' };
  }

  // Add completion status if we have duration
  let action = activityInfo.action;
  if (data.duration_ms !== undefined) {
    const durationSec = (data.duration_ms / 1000).toFixed(1);
    const statusIcon = data.success !== false ? '✓' : '✗';
    action = `${action} ${statusIcon} (${durationSec}s)`;
  }

  return {
    id: `activity-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type: activityInfo.type,
    timestamp,
    actor: formatAgentName(agentName),
    action,
    target: toolName,
    durationMs: data.duration_ms,
    success: data.success,
    operationId: data.operation_id,
    details: data.mcp_server ? `via ${data.mcp_server}` : undefined,
  };
}
