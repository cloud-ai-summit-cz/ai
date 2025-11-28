/**
 * Mock data for development and prototyping.
 * 
 * This simulates the SSE events that would come from the research orchestrator.
 * Replace with real API calls when connecting to the backend.
 */

import type { Task, Note, DraftSection, Question, ChatMessage } from './types';

// === Mock Plan/Tasks ===

export const mockTasks: Task[] = [
  {
    id: 't1',
    description: 'Analyze market size and growth trends',
    status: 'completed',
    assignedTo: 'market-analyst',
    completedAt: '2025-11-28T10:05:00Z',
  },
  {
    id: 't2',
    description: 'Identify customer segments and preferences',
    status: 'completed',
    assignedTo: 'market-analyst',
    completedAt: '2025-11-28T10:08:00Z',
  },
  {
    id: 't3',
    description: 'Profile top 3-5 competitors',
    status: 'in-progress',
    assignedTo: 'competitor-analyst',
  },
  {
    id: 't4',
    description: 'Identify competitive positioning gaps',
    status: 'pending',
    assignedTo: 'competitor-analyst',
  },
  {
    id: 't5',
    description: 'Evaluate 2-3 potential locations',
    status: 'pending',
    assignedTo: 'location-scout',
  },
  {
    id: 't6',
    description: 'List key regulations and requirements',
    status: 'pending',
    assignedTo: 'location-scout',
  },
  {
    id: 't7',
    description: 'Create financial projection',
    status: 'pending',
    assignedTo: 'finance-analyst',
  },
  {
    id: 't8',
    description: 'Write final recommendation',
    status: 'pending',
    assignedTo: 'synthesizer',
  },
];

// === Mock Notes ===

export const mockNotes: Note[] = [
  {
    id: 'n1',
    content: 'Vienna coffee market valued at €420M annually with 3.2% YoY growth',
    author: 'market-analyst',
    timestamp: '2025-11-28T10:02:00Z',
    tags: ['market-size', 'vienna', 'growth'],
  },
  {
    id: 'n2',
    content: 'Specialty coffee segment growing at 8.5%, outpacing traditional cafés',
    author: 'market-analyst',
    timestamp: '2025-11-28T10:03:00Z',
    tags: ['specialty-coffee', 'trends'],
  },
  {
    id: 'n3',
    content: 'Target demographic: Urban professionals 25-45, average spend €4.80/visit',
    author: 'market-analyst',
    timestamp: '2025-11-28T10:06:00Z',
    tags: ['demographics', 'customer-segment'],
  },
  {
    id: 'n4',
    content: 'Key competitor: Aida Café - 15 locations, traditional positioning, €3.50 avg',
    author: 'competitor-analyst',
    timestamp: '2025-11-28T10:12:00Z',
    tags: ['competitor', 'aida'],
  },
  {
    id: 'n5',
    content: 'Starbucks presence: 12 locations in Vienna, premium pricing €5.20 avg',
    author: 'competitor-analyst',
    timestamp: '2025-11-28T10:14:00Z',
    tags: ['competitor', 'starbucks'],
  },
];

// === Mock Draft Sections ===

export const mockDraftSections: DraftSection[] = [
  {
    id: 'executive-summary',
    title: 'Executive Summary',
    content: `## Executive Summary

*This section will be completed by the Synthesizer agent after all research is gathered.*

**Status**: Awaiting completion of all research tasks.`,
    lastUpdatedBy: 'synthesizer',
    lastUpdatedAt: '2025-11-28T10:00:00Z',
    version: 1,
  },
  {
    id: 'market-analysis',
    title: 'Market Analysis',
    content: `## Market Analysis

### Market Size & Growth
The Vienna coffee market is valued at approximately **€420 million annually**, with a steady year-over-year growth rate of **3.2%**. The specialty coffee segment is particularly dynamic, growing at **8.5%** annually.

### Key Trends
- Growing preference for specialty and third-wave coffee
- Increased demand for sustainable and ethically sourced beans
- Rise of remote work driving demand for café workspaces

### Customer Segments
| Segment | Size | Avg Spend | Frequency |
|---------|------|-----------|-----------|
| Urban Professionals | 45% | €4.80 | 4x/week |
| Students | 25% | €3.20 | 3x/week |
| Tourists | 20% | €5.50 | Occasional |
| Seniors | 10% | €3.80 | 5x/week |`,
    lastUpdatedBy: 'market-analyst',
    lastUpdatedAt: '2025-11-28T10:08:00Z',
    version: 3,
  },
  {
    id: 'competitive-landscape',
    title: 'Competitive Landscape',
    content: `## Competitive Landscape

### Major Players

**Currently analyzing...**

1. **Aida Café** - Traditional Viennese chain
   - 15 locations across Vienna
   - Traditional positioning, local favorite
   - Average price: €3.50

2. **Starbucks**
   - 12 locations
   - Premium positioning, tourist-heavy
   - Average price: €5.20

3. *(More competitors being analyzed...)*`,
    lastUpdatedBy: 'competitor-analyst',
    lastUpdatedAt: '2025-11-28T10:14:00Z',
    version: 2,
  },
];

// === Mock Questions ===

export const mockQuestions: Question[] = [
  {
    id: 'q1',
    text: 'What is your target budget range for the initial investment?',
    context: 'This will help us refine the financial projections and location recommendations.',
    askedBy: 'finance-analyst',
    priority: 'high',
    blocking: true,
    options: ['€100k - €200k', '€200k - €350k', '€350k - €500k', '€500k+'],
    createdAt: '2025-11-28T10:15:00Z',
  },
  {
    id: 'q2',
    text: 'Do you have a preference for district/neighborhood?',
    context: 'Vienna has distinct neighborhoods with different customer profiles and rental costs.',
    askedBy: 'location-scout',
    priority: 'medium',
    blocking: false,
    createdAt: '2025-11-28T10:16:00Z',
  },
];

// === Mock Chat Messages ===

export const mockMessages: ChatMessage[] = [
  {
    id: 'm1',
    type: 'system',
    sender: 'System',
    content: 'Research session started for: "Should Cofilot expand to Vienna?"',
    timestamp: '2025-11-28T10:00:00Z',
  },
  {
    id: 'm2',
    type: 'orchestrator',
    sender: 'Orchestrator',
    content: 'Initializing research workflow. Creating task plan and assigning agents.',
    timestamp: '2025-11-28T10:00:05Z',
  },
  {
    id: 'm3',
    type: 'orchestrator',
    sender: 'Orchestrator',
    content: 'Assigned market analysis tasks to Market Analyst agent.',
    timestamp: '2025-11-28T10:00:10Z',
  },
  {
    id: 'm4',
    type: 'agent',
    sender: 'Market Analyst',
    content: 'Starting market size analysis for Vienna coffee sector.',
    timestamp: '2025-11-28T10:01:00Z',
    metadata: { agentType: 'market-analyst', status: 'started' },
  },
  {
    id: 'm5',
    type: 'tool',
    sender: 'Market Analyst',
    content: 'Called web_search: "Vienna coffee market size 2024"',
    timestamp: '2025-11-28T10:01:30Z',
    metadata: { toolName: 'web_search', status: 'started' },
  },
  {
    id: 'm6',
    type: 'tool',
    sender: 'Market Analyst',
    content: 'web_search completed (1.2s)',
    timestamp: '2025-11-28T10:01:32Z',
    metadata: { toolName: 'web_search', status: 'completed', duration: 1200 },
  },
  {
    id: 'm7',
    type: 'agent',
    sender: 'Market Analyst',
    content: 'Added note: Vienna coffee market valued at €420M annually',
    timestamp: '2025-11-28T10:02:00Z',
    metadata: { agentType: 'market-analyst' },
  },
  {
    id: 'm8',
    type: 'agent',
    sender: 'Market Analyst',
    content: 'Market analysis complete. Updated Draft section.',
    timestamp: '2025-11-28T10:08:00Z',
    metadata: { agentType: 'market-analyst', status: 'completed' },
  },
  {
    id: 'm9',
    type: 'orchestrator',
    sender: 'Orchestrator',
    content: 'Market Analyst completed. Assigning Competitor Analyst.',
    timestamp: '2025-11-28T10:08:10Z',
  },
  {
    id: 'm10',
    type: 'agent',
    sender: 'Competitor Analyst',
    content: 'Beginning competitive landscape analysis.',
    timestamp: '2025-11-28T10:10:00Z',
    metadata: { agentType: 'competitor-analyst', status: 'started' },
  },
  {
    id: 'm11',
    type: 'agent',
    sender: 'Competitor Analyst',
    content: 'Identified major competitor: Aida Café (15 locations)',
    timestamp: '2025-11-28T10:12:00Z',
    metadata: { agentType: 'competitor-analyst' },
  },
  {
    id: 'm12',
    type: 'agent',
    sender: 'Competitor Analyst',
    content: 'Analyzing Starbucks presence in Vienna...',
    timestamp: '2025-11-28T10:14:00Z',
    metadata: { agentType: 'competitor-analyst' },
  },
];

// === Mock SSE Event Simulation ===

/**
 * Simulates SSE events for demo purposes.
 * Call this to add new events to the store at intervals.
 */
export function createMockEventStream(
  onEvent: (event: {
    type: 'message' | 'task_update' | 'note_added' | 'draft_updated' | 'question_asked';
    data: unknown;
  }) => void
) {
  const events = [
    {
      delay: 2000,
      event: {
        type: 'message' as const,
        data: {
          id: 'm13',
          type: 'agent',
          sender: 'Competitor Analyst',
          content: 'Found 3 specialty coffee competitors in the market.',
          timestamp: new Date().toISOString(),
          metadata: { agentType: 'competitor-analyst' },
        },
      },
    },
    {
      delay: 4000,
      event: {
        type: 'note_added' as const,
        data: {
          id: 'n6',
          content: 'Gap identified: No specialty roaster with direct-trade sourcing in Vienna',
          author: 'competitor-analyst',
          timestamp: new Date().toISOString(),
          tags: ['gap', 'opportunity'],
        },
      },
    },
    {
      delay: 6000,
      event: {
        type: 'task_update' as const,
        data: {
          id: 't3',
          status: 'completed',
          completedAt: new Date().toISOString(),
        },
      },
    },
    {
      delay: 7000,
      event: {
        type: 'task_update' as const,
        data: {
          id: 't4',
          status: 'in-progress',
        },
      },
    },
    {
      delay: 8000,
      event: {
        type: 'message' as const,
        data: {
          id: 'm14',
          type: 'orchestrator',
          sender: 'Orchestrator',
          content: 'Competitor analysis progressing. 2/4 tasks complete.',
          timestamp: new Date().toISOString(),
        },
      },
    },
  ];

  let timeoutIds: number[] = [];

  events.forEach(({ delay, event }) => {
    const id = window.setTimeout(() => {
      onEvent(event);
    }, delay);
    timeoutIds.push(id);
  });

  // Return cleanup function
  return () => {
    timeoutIds.forEach(clearTimeout);
  };
}
