/**
 * Zustand store for application state management.
 *
 * Manages the entire research session state including:
 * - Session metadata
 * - Scratchpad pillars (Plan, Notes, Draft, Questions)
 * - Chat messages
 * - UI state
 */

import { create } from 'zustand';
import type {
  ResearchSession,
  Task,
  TaskStatus,
  Note,
  DraftSection,
  Question,
  ChatMessage,
  ScratchpadState,
  SessionStatus,
  SSEEvent,
  SSEEventType,
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
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;

  // Notes actions
  setNotes: (notes: Note[]) => void;
  addNote: (note: Note) => void;

  // Draft actions
  setDraftSections: (sections: DraftSection[]) => void;
  updateDraftSection: (section: DraftSection) => void;

  // Questions actions
  setQuestions: (questions: Question[]) => void;
  addQuestion: (question: Question) => void;
  answerQuestion: (questionId: string, answer: string) => void;

  // === Chat State ===
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;

  // === UI State ===
  isConnected: boolean;
  setConnected: (connected: boolean) => void;
  activePanel: 'chat' | 'plan' | 'notes' | 'draft';
  setActivePanel: (panel: 'chat' | 'plan' | 'notes' | 'draft') => void;
  showQuestionModal: boolean;
  setShowQuestionModal: (show: boolean) => void;

  // === SSE & Workflow ===
  sseCleanup: (() => void) | null;
  pollingInterval: ReturnType<typeof setInterval> | null;
  startResearchSession: (query: string) => Promise<void>;
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

  addTask: (task) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        plan: [...state.scratchpad.plan, task],
      },
    })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        plan: state.scratchpad.plan.map((task) =>
          task.id === taskId ? { ...task, ...updates } : task
        ),
      },
    })),

  setNotes: (notes) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, notes },
    })),

  addNote: (note) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        notes: [...state.scratchpad.notes, note],
      },
    })),

  setDraftSections: (sections) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, draft: sections },
    })),

  updateDraftSection: (section) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        draft: state.scratchpad.draft.some((s) => s.id === section.id)
          ? state.scratchpad.draft.map((s) =>
              s.id === section.id ? section : s
            )
          : [...state.scratchpad.draft, section],
      },
    })),

  setQuestions: (questions) =>
    set((state) => ({
      scratchpad: { ...state.scratchpad, questions },
    })),

  addQuestion: (question) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        questions: [...state.scratchpad.questions, question],
      },
      // Auto-show modal for blocking questions
      showQuestionModal: question.blocking || state.showQuestionModal,
    })),

  answerQuestion: (questionId, answer) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        questions: state.scratchpad.questions.map((q) =>
          q.id === questionId
            ? { ...q, answer, answeredAt: new Date().toISOString() }
            : q
        ),
      },
    })),

  // === Chat State ===
  messages: [],
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  clearMessages: () => set({ messages: [] }),

  // === UI State ===
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),
  activePanel: 'chat',
  setActivePanel: (panel) => {
    set({ activePanel: panel });
    // Re-fetch scratchpad data when switching tabs (except chat)
    if (panel !== 'chat') {
      get().pollScratchpadState().catch((err) => {
        console.debug('Failed to refresh scratchpad on tab switch:', err);
      });
    }
  },
  showQuestionModal: false,
  setShowQuestionModal: (show) => set({ showQuestionModal: show }),

  // === SSE & Workflow ===
  sseCleanup: null,
  pollingInterval: null,

  startPolling: () => {
    const store = get();
    // Clear any existing polling interval
    if (store.pollingInterval) {
      clearInterval(store.pollingInterval);
    }
    
    // Poll scratchpad every 5 seconds while session is running
    const interval = setInterval(() => {
      const currentStore = get();
      if (currentStore.session?.status === 'running') {
        currentStore.pollScratchpadState().catch((err) => {
          console.debug('Background poll failed:', err);
        });
      } else {
        // Stop polling if session is no longer running
        currentStore.stopPolling();
      }
    }, 5000);
    
    set({ pollingInterval: interval });
    console.log('Started background scratchpad polling (5s interval)');
  },

  stopPolling: () => {
    const store = get();
    if (store.pollingInterval) {
      clearInterval(store.pollingInterval);
      set({ pollingInterval: null });
      console.log('Stopped background scratchpad polling');
    }
  },

  startResearchSession: async (query: string) => {
    const store = get();

    // Clean up any existing SSE connection and polling
    if (store.sseCleanup) {
      store.sseCleanup();
    }
    store.stopPolling();

    // Reset state for new session
    set({
      scratchpad: initialScratchpad,
      messages: [],
      isConnected: false,
    });

    try {
      // Create session via API
      const session = await createSession(query);
      set({ session });

      // Add initial system message
      store.addMessage({
        id: `msg-${Date.now()}`,
        type: 'system',
        sender: 'System',
        content: `Research session started for: "${query}"`,
        timestamp: new Date().toISOString(),
      });

      // Start SSE streaming
      const cleanup = startSession(
        session.sessionId,
        (event) => get().handleSSEEvent(event),
        (error) => {
          console.error('SSE error:', error);
          set({ isConnected: false });
          get().addMessage({
            id: `msg-${Date.now()}`,
            type: 'error',
            sender: 'System',
            content: `Connection error: ${error.message}`,
            timestamp: new Date().toISOString(),
          });
        },
        () => {
          set({ isConnected: false });
        }
      );

      set({ sseCleanup: cleanup, isConnected: true });
      
      // Start background polling for scratchpad updates
      // This ensures we get updates even if SSE events are missed
      store.startPolling();
    } catch (error) {
      console.error('Failed to start research session:', error);
      store.addMessage({
        id: `msg-${Date.now()}`,
        type: 'error',
        sender: 'System',
        content: `Failed to start session: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      });
    }
  },

  handleSSEEvent: (event: SSEEvent) => {
    const store = get();
    const eventType = event.event_type as SSEEventType;
    const data = event.data as Record<string, unknown>;
    const timestamp = event.timestamp;

    switch (eventType) {
      // === Session Lifecycle ===
      case 'session_started':
        store.updateSessionStatus('running');
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'orchestrator',
          sender: 'Orchestrator',
          content: (data.message as string) || 'Research workflow initialized',
          timestamp,
        });
        break;

      case 'workflow_completed':
        store.updateSessionStatus('completed');
        store.stopPolling();
        // Final poll to get any remaining updates
        store.pollScratchpadState().catch(() => {});
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'system',
          sender: 'System',
          content: 'Research workflow completed successfully',
          timestamp,
        });
        break;

      case 'workflow_failed':
        store.updateSessionStatus('failed');
        store.stopPolling();
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'error',
          sender: 'System',
          content: `Workflow failed: ${data.error || 'Unknown error'}`,
          timestamp,
        });
        break;

      // === Agent Events ===
      case 'agent_started':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: formatAgentName(data.agent_name as string),
          content: (data.task_description as string) || 'Starting analysis...',
          timestamp,
          metadata: {
            agentType: data.agent_name as string,
            status: 'started',
          },
        });
        break;

      case 'agent_progress':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: formatAgentName(data.agent_name as string),
          content: data.chunk as string,
          timestamp,
          metadata: { agentType: data.agent_name as string },
        });
        break;

      case 'agent_thinking':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: formatAgentName(data.agent_name as string),
          content: `💭 ${data.message as string}`,
          timestamp,
          metadata: { agentType: data.agent_name as string },
        });
        break;

      case 'agent_completed':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: formatAgentName(data.agent_name as string),
          content: (data.content as string) || (data.result_summary as string) || 'Analysis complete',
          timestamp,
          metadata: {
            agentType: data.agent_name as string,
            status: 'completed',
            duration: data.execution_time_ms as number,
          },
        });
        break;

      case 'agent_failed':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'error',
          sender: formatAgentName(data.agent_name as string),
          content: `Agent failed: ${data.error || 'Unknown error'}`,
          timestamp,
          metadata: {
            agentType: data.agent_name as string,
            status: 'failed',
          },
        });
        break;

      case 'agent_response':
        // Subagent returned - show a brief message and poll scratchpad
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: formatAgentName(data.agent_name as string),
          content: `📥 Analysis complete. View findings in Notes and Draft tabs.`,
          timestamp,
          metadata: {
            agentType: data.agent_name as string,
            status: 'completed',
            duration: data.execution_time_ms as number,
          },
        });
        // Note: pollScratchpadState is called automatically after this event
        break;

      // === Tool Events ===
      case 'tool_call_started': {
        const toolName = data.tool_name as string;
        const agentName = data.agent_name as string;
        const inputArgs = data.input_args as Record<string, unknown> | undefined;
        
        // Agent-to-agent tools show the actual message being sent
        const isAgentTool = ['market_analysis', 'competitor_analysis', 'synthesize_findings'].includes(toolName);
        
        if (isAgentTool && inputArgs) {
          // Extract the query/context being sent to the agent
          const agentQuery = (inputArgs.query || inputArgs.context || '') as string;
          const targetAgent = formatAgentName(toolName.replace('_', '-'));
          
          // Show the orchestrator sending a message to the specialist agent
          store.addMessage({
            id: `msg-${Date.now()}-delegate`,
            type: 'orchestrator',
            sender: formatAgentName(agentName),
            content: `📤 Delegating to ${targetAgent}: "${agentQuery.slice(0, 200)}${agentQuery.length > 200 ? '...' : ''}"`,
            timestamp,
            metadata: {
              toolName,
              targetAgent,
              status: 'started',
            },
          });
        } else {
          store.addMessage({
            id: `msg-${Date.now()}`,
            type: 'tool',
            sender: formatAgentName(agentName),
            content: `Calling ${toolName}...`,
            timestamp,
            metadata: {
              toolName,
              status: 'started',
            },
          });
        }
        break;
      }

      case 'tool_call_completed': {
        const toolName = data.tool_name as string;
        const agentName = data.agent_name as string;
        const isAgentTool = ['market_analysis', 'competitor_analysis', 'synthesize_findings'].includes(toolName);
        
        if (isAgentTool) {
          const targetAgent = formatAgentName(toolName.replace('_', '-'));
          store.addMessage({
            id: `msg-${Date.now()}-response`,
            type: 'agent',
            sender: targetAgent,
            content: `📥 Response received (${data.execution_time_ms}ms)`,
            timestamp,
            metadata: {
              toolName,
              status: 'completed',
              duration: data.execution_time_ms as number,
            },
          });
        } else {
          store.addMessage({
            id: `msg-${Date.now()}`,
            type: 'tool',
            sender: formatAgentName(agentName),
            content: `${toolName} completed (${data.execution_time_ms}ms)`,
            timestamp,
            metadata: {
              toolName,
              status: 'completed',
              duration: data.execution_time_ms as number,
            },
          });
        }
        break;
      }

      case 'tool_call_failed':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'tool',
          sender: formatAgentName(data.agent_name as string),
          content: `${data.tool_name} failed: ${data.error}`,
          timestamp,
          metadata: {
            toolName: data.tool_name as string,
            status: 'failed',
          },
        });
        break;

      // === Scratchpad Events ===
      case 'scratchpad_updated':
        handleScratchpadUpdate(store, data, timestamp);
        break;

      case 'scratchpad_snapshot':
        handleScratchpadSnapshot(store, data);
        break;

      // === Question Events ===
      case 'question_added':
        store.addQuestion({
          id: data.question_id as string,
          text: data.question as string,
          context: data.context as string | undefined,
          askedBy: data.asked_by as string,
          priority: (data.priority as 'high' | 'medium' | 'low') || 'medium',
          blocking: (data.blocking as boolean) || false,
          options: data.options as string[] | undefined,
          createdAt: timestamp,
        });
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'orchestrator',
          sender: formatAgentName(data.asked_by as string),
          content: `❓ ${data.question as string}`,
          timestamp,
        });
        break;

      case 'question_answered':
        store.answerQuestion(data.question_id as string, data.answer as string);
        break;

      // === Synthesis Events ===
      case 'synthesis_started':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'orchestrator',
          sender: 'Synthesizer',
          content: (data.message as string) || 'Compiling final report...',
          timestamp,
          metadata: { agentType: 'synthesizer', status: 'started' },
        });
        break;

      case 'synthesis_progress':
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: 'Synthesizer',
          content: data.chunk as string,
          timestamp,
          metadata: { agentType: 'synthesizer' },
        });
        break;

      case 'synthesis_completed':
        store.updateDraftSection({
          id: 'final-report',
          title: 'Final Report',
          content: data.final_report as string,
          lastUpdatedBy: 'synthesizer',
          lastUpdatedAt: timestamp,
          version: 1,
        });
        store.addMessage({
          id: `msg-${Date.now()}`,
          type: 'agent',
          sender: 'Synthesizer',
          content: 'Final report complete',
          timestamp,
          metadata: { agentType: 'synthesizer', status: 'completed' },
        });
        break;

      // === Keep-Alive ===
      case 'heartbeat':
        // Heartbeat event - just confirms connection is alive, no UI update needed
        console.debug('SSE heartbeat received');
        break;

      default:
        console.warn(`Unhandled SSE event type: ${eventType}`);
    }

    // Poll scratchpad after events that may have changed state
    // (agent and tool events, since subagents write directly to scratchpad)
    const pollTriggerEvents: SSEEventType[] = [
      'agent_completed',
      'agent_response',
      'tool_call_completed',
      'synthesis_completed',
      'workflow_completed',
      'scratchpad_updated', // Fallback for orchestrator-only updates
    ];
    
    if (pollTriggerEvents.includes(eventType)) {
      // Poll asynchronously without blocking
      store.pollScratchpadState().catch((err) => {
        console.warn('Failed to poll scratchpad:', err);
      });
    }
  },

  pollScratchpadState: async () => {
    const store = get();
    const session = store.session;
    
    if (!session) {
      return;
    }

    try {
      const { plan, notes, draft } = await pollScratchpad(session.sessionId);

      // Update plan/tasks
      if (plan && plan.tasks.length > 0) {
        const tasks: Task[] = plan.tasks.map((t) => ({
          id: t.task_id,
          description: t.description,
          status: t.status as TaskStatus,
          assignedTo: t.assigned_to,
          createdAt: t.created_at || new Date().toISOString(),
        }));
        set((state) => ({
          scratchpad: { ...state.scratchpad, plan: tasks },
        }));
      }

      // Update notes
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

      // Update draft sections
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
      // Log but don't fail - scratchpad polling is best-effort
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
      messages: [],
      isConnected: false,
      activePanel: 'chat',
      showQuestionModal: false,
      sseCleanup: null,
      pollingInterval: null,
    });
  },
}));

/**
 * Format agent name for display.
 */
function formatAgentName(agentName: string): string {
  if (!agentName) return 'Agent';
  return agentName
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Handle scratchpad_updated events and update appropriate pillar.
 * Uses tool_type field for reliable routing instead of section name patterns.
 */
function handleScratchpadUpdate(
  store: ResearchStore,
  data: Record<string, unknown>,
  timestamp: string
): void {
  const sectionName = (data.section_name as string) || '';
  const updatedBy = data.updated_by as string;
  const contentPreview = data.content_preview as string;
  const toolType = data.tool_type as string;
  const tasksCreated = data.tasks_created as number | undefined;
  const tasksArray = data.tasks as Array<{
    description?: string;
    priority?: string;
    assigned_to?: string;
    status?: string;
    task_id?: string;  // Server-assigned ID from add_tasks output
  }> | undefined;

  // Route based on tool_type (preferred) or section_name (fallback)
  if (toolType === 'add_tasks' || sectionName === 'plan') {
    // Handle task additions - prefer full tasks array over parsing contentPreview
    if (tasksArray && tasksArray.length > 0) {
      tasksArray.forEach((task, idx) => {
        store.addTask({
          // Use server-assigned task_id if available, otherwise generate one
          id: task.task_id || `task-${Date.now()}-${idx}`,
          description: task.description || 'Unknown task',
          status: (task.status as Task['status']) || 'pending',
          assignedTo: task.assigned_to || updatedBy,
          createdAt: timestamp,
        });
      });
      store.addMessage({
        id: `msg-${Date.now()}`,
        type: 'orchestrator',
        sender: formatAgentName(updatedBy),
        content: `📋 Added ${tasksArray.length} task${tasksArray.length > 1 ? 's' : ''} to plan`,
        timestamp,
      });
    } else if (contentPreview) {
      // Fallback: parse from contentPreview if tasks array not available
      const taskCount = tasksCreated || 1;
      store.addMessage({
        id: `msg-${Date.now()}`,
        type: 'orchestrator',
        sender: formatAgentName(updatedBy),
        content: `📋 Added ${taskCount} task${taskCount > 1 ? 's' : ''} to plan`,
        timestamp,
      });
      const taskDescriptions = contentPreview.split(';').map(t => t.trim()).filter(Boolean);
      taskDescriptions.forEach((description, idx) => {
        store.addTask({
          id: `task-${Date.now()}-${idx}`,
          description,
          status: 'pending',
          assignedTo: updatedBy,
          createdAt: timestamp,
        });
      });
    }
  } else if (toolType === 'update_task') {
    // Handle task status updates
    const taskUpdate = data.task_update as { task_id?: string; status?: string; assigned_to?: string } | undefined;
    if (taskUpdate?.task_id) {
      store.updateTask(taskUpdate.task_id, {
        status: (taskUpdate.status as Task['status']) || 'pending',
        ...(taskUpdate.assigned_to && { assignedTo: taskUpdate.assigned_to }),
      });
      store.addMessage({
        id: `msg-${Date.now()}`,
        type: 'orchestrator',
        sender: formatAgentName(updatedBy),
        content: `✅ Task updated: ${taskUpdate.task_id} → ${taskUpdate.status || 'updated'}`,
        timestamp,
      });
    }
  } else if (toolType === 'add_note' || sectionName === 'notes') {
    // Handle notes additions
    if (contentPreview) {
      store.addNote({
        id: `note-${Date.now()}`,
        content: contentPreview,
        author: updatedBy,
        timestamp,
        tags: [],
      });
    }
    store.addMessage({
      id: `msg-${Date.now()}`,
      type: 'orchestrator',
      sender: formatAgentName(updatedBy),
      content: `📝 Added note`,
      timestamp,
    });
  } else if (toolType === 'write_draft_section' || sectionName) {
    // Handle draft section updates
    store.updateDraftSection({
      id: sectionName,
      title: formatSectionTitle(sectionName),
      content: contentPreview || '',
      lastUpdatedBy: updatedBy,
      lastUpdatedAt: timestamp,
      version: 1,
    });
    store.addMessage({
      id: `msg-${Date.now()}`,
      type: 'orchestrator',
      sender: formatAgentName(updatedBy),
      content: `📝 Updated draft: ${formatSectionTitle(sectionName)}`,
      timestamp,
    });
  }
}

/**
 * Handle scratchpad_snapshot events and populate state.
 * Sections with names starting with "note:" or "task:" are routed appropriately.
 */
function handleScratchpadSnapshot(
  store: ResearchStore,
  data: Record<string, unknown>
): void {
  const sections = data.sections as Array<{
    name: string;
    content: string;
    updated_by?: string;
    updated_at?: string;
  }>;

  if (!sections) return;

  const drafts: DraftSection[] = [];
  const notes: Note[] = [];
  const tasks: Task[] = [];

  sections.forEach((section) => {
    if (section.name.startsWith('note:')) {
      // This is a note
      notes.push({
        id: section.name.replace('note:', ''),
        content: section.content,
        author: section.updated_by || 'unknown',
        timestamp: section.updated_at || new Date().toISOString(),
        tags: [],
      });
    } else if (section.name.startsWith('task:')) {
      // This is a task - parse "[status] description" format
      const taskId = section.name.replace('task:', '');
      const match = section.content.match(/^\[(\w+)\]\s*(.*)$/);
      const status = match ? match[1] : 'pending';
      const description = match ? match[2] : section.content;
      tasks.push({
        id: taskId,
        description,
        status: status as Task['status'],
        assignedTo: section.updated_by,
        createdAt: section.updated_at || new Date().toISOString(),
      });
    } else {
      // This is a draft section
      drafts.push({
        id: section.name,
        title: formatSectionTitle(section.name),
        content: section.content,
        lastUpdatedBy: section.updated_by,
        lastUpdatedAt: section.updated_at,
        version: 1,
      });
    }
  });

  if (drafts.length > 0) {
    store.setDraftSections(drafts);
  }
  if (notes.length > 0) {
    store.setNotes(notes);
  }
  if (tasks.length > 0) {
    store.setTasks(tasks);
  }
}

/**
 * Format section name as title.
 */
function formatSectionTitle(sectionName: string): string {
  return sectionName
    .replace(/[-_]/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
