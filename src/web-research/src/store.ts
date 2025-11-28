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
  Note,
  DraftSection,
  Question,
  ChatMessage,
  ScratchpadState,
  SessionStatus,
  TaskStatus,
} from './types';
import {
  mockTasks,
  mockNotes,
  mockDraftSections,
  mockQuestions,
  mockMessages,
} from './mocks/data';

interface ResearchStore {
  // === Session State ===
  session: ResearchSession | null;
  setSession: (session: ResearchSession | null) => void;
  updateSessionStatus: (status: SessionStatus) => void;

  // === Scratchpad State ===
  scratchpad: ScratchpadState;
  
  // Plan actions
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  
  // Notes actions
  addNote: (note: Note) => void;
  
  // Draft actions
  updateDraftSection: (section: DraftSection) => void;
  
  // Questions actions
  addQuestion: (question: Question) => void;
  answerQuestion: (questionId: string, answer: string) => void;

  // === Chat State ===
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;

  // === UI State ===
  isConnected: boolean;
  setConnected: (connected: boolean) => void;
  activePanel: 'chat' | 'plan' | 'notes' | 'draft';
  setActivePanel: (panel: 'chat' | 'plan' | 'notes' | 'draft') => void;
  showQuestionModal: boolean;
  setShowQuestionModal: (show: boolean) => void;
  
  // === Mock Data Loading ===
  loadMockData: () => void;
  resetState: () => void;
}

const initialScratchpad: ScratchpadState = {
  plan: [],
  notes: [],
  draft: [],
  questions: [],
};

export const useResearchStore = create<ResearchStore>((set) => ({
  // === Session State ===
  session: null,
  setSession: (session) => set({ session }),
  updateSessionStatus: (status) =>
    set((state) => ({
      session: state.session ? { ...state.session, status } : null,
    })),

  // === Scratchpad State ===
  scratchpad: initialScratchpad,

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

  addNote: (note) =>
    set((state) => ({
      scratchpad: {
        ...state.scratchpad,
        notes: [...state.scratchpad.notes, note],
      },
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

  // === UI State ===
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),
  activePanel: 'chat',
  setActivePanel: (panel) => set({ activePanel: panel }),
  showQuestionModal: false,
  setShowQuestionModal: (show) => set({ showQuestionModal: show }),

  // === Mock Data Loading ===
  loadMockData: () =>
    set({
      session: {
        sessionId: 'mock-session-001',
        query: 'Should Cofilot expand to Vienna?',
        status: 'running',
        createdAt: '2025-11-28T10:00:00Z',
        startedAt: '2025-11-28T10:00:00Z',
      },
      scratchpad: {
        plan: mockTasks,
        notes: mockNotes,
        draft: mockDraftSections,
        questions: mockQuestions,
      },
      messages: mockMessages,
      isConnected: true,
    }),

  resetState: () =>
    set({
      session: null,
      scratchpad: initialScratchpad,
      messages: [],
      isConnected: false,
      activePanel: 'chat',
      showQuestionModal: false,
    }),
}));
