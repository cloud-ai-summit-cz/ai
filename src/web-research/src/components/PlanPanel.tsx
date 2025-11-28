/**
 * Plan Panel Component
 * 
 * Displays the research checklist/plan from the Scratchpad.
 * Shows task status with visual indicators.
 */

import { 
  CheckCircle2, 
  Circle, 
  Loader2, 
  XCircle,
  SkipForward,
  ListTodo
} from 'lucide-react';
import type { Task, TaskStatus } from '../types';

interface PlanPanelProps {
  tasks: Task[];
}

function getStatusIcon(status: TaskStatus) {
  const baseClass = "w-5 h-5";
  
  switch (status) {
    case 'completed':
      return <CheckCircle2 className={`${baseClass} text-green-500`} />;
    case 'in-progress':
      return <Loader2 className={`${baseClass} text-accent animate-spin`} />;
    case 'failed':
      return <XCircle className={`${baseClass} text-red-500`} />;
    case 'skipped':
      return <SkipForward className={`${baseClass} text-text-dim`} />;
    case 'pending':
    default:
      return <Circle className={`${baseClass} text-text-dim`} />;
  }
}

function getStatusBadge(status: TaskStatus): { text: string; className: string } {
  switch (status) {
    case 'completed':
      return { text: 'Done', className: 'bg-green-500/20 text-green-400' };
    case 'in-progress':
      return { text: 'Running', className: 'bg-accent/20 text-accent' };
    case 'failed':
      return { text: 'Failed', className: 'bg-red-500/20 text-red-400' };
    case 'skipped':
      return { text: 'Skipped', className: 'bg-text-dim/20 text-text-dim' };
    case 'pending':
    default:
      return { text: 'Pending', className: 'bg-surface-lighter text-text-muted' };
  }
}

function getAgentColor(agent?: string): string {
  if (!agent) return 'text-text-muted';
  
  switch (agent) {
    case 'market-analyst':
      return 'text-blue-400';
    case 'competitor-analyst':
      return 'text-purple-400';
    case 'location-scout':
      return 'text-orange-400';
    case 'finance-analyst':
      return 'text-green-400';
    case 'synthesizer':
      return 'text-accent';
    default:
      return 'text-text-muted';
  }
}

function TaskItem({ task, index }: { task: Task; index: number }) {
  const badge = getStatusBadge(task.status);
  
  return (
    <div 
      className={`
        p-4 border-b border-border/30 last:border-b-0
        ${task.status === 'in-progress' ? 'bg-surface-light/50' : ''}
        ${task.status === 'completed' ? 'opacity-70' : ''}
        transition-all duration-200
      `}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {getStatusIcon(task.status)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-text-dim text-xs font-mono">#{index + 1}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}>
              {badge.text}
            </span>
          </div>
          <p className={`text-sm ${task.status === 'completed' ? 'line-through text-text-muted' : 'text-text'}`}>
            {task.description}
          </p>
          {task.assignedTo && (
            <p className={`text-xs mt-1 ${getAgentColor(task.assignedTo)}`}>
              → {task.assignedTo}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function PlanPanel({ tasks }: PlanPanelProps) {
  const completedCount = tasks.filter(t => t.status === 'completed').length;
  const totalCount = tasks.length;
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  
  return (
    <div className="flex flex-col h-full">
      {/* Progress Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <ListTodo className="w-4 h-4 text-text-muted" />
            <span className="text-sm font-medium text-text">Research Plan</span>
          </div>
          <span className="text-sm text-text-muted">
            {completedCount}/{totalCount}
          </span>
        </div>
        <div className="w-full bg-surface-dark rounded-full h-2">
          <div 
            className="bg-accent h-2 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>
      
      {/* Task List */}
      <div className="flex-1 overflow-y-auto">
        {tasks.length === 0 ? (
          <div className="p-8 text-center text-text-muted">
            <ListTodo className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No tasks yet</p>
            <p className="text-sm mt-1">Tasks will appear as the workflow progresses</p>
          </div>
        ) : (
          tasks.map((task, index) => (
            <TaskItem key={task.id} task={task} index={index} />
          ))
        )}
      </div>
    </div>
  );
}
