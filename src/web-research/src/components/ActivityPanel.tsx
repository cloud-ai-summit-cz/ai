/**
 * Activity Panel Component
 * 
 * Displays the research workflow timeline based on trace events.
 * Shows agent delegations, tool calls, and scratchpad updates.
 */

import { useEffect, useRef, useState } from 'react';
import { 
  Bot, 
  ArrowRight,
  CheckCircle2,
  XCircle,
  Cpu,
  FileText,
  Search,
  ListTodo,
  Sparkles,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { Activity, ActivityType } from '../types';

interface ActivityPanelProps {
  activities: Activity[];
  onNavigate?: (panel: 'plan' | 'notes' | 'draft') => void;
}

function getActivityIcon(type: ActivityType, success?: boolean) {
  const iconClass = "w-4 h-4 flex-shrink-0";
  
  switch (type) {
    case 'workflow_start':
      return <Sparkles className={`${iconClass} text-accent`} />;
    case 'workflow_complete':
      return <CheckCircle2 className={`${iconClass} text-green-400`} />;
    case 'workflow_error':
      return <XCircle className={`${iconClass} text-red-400`} />;
    case 'agent_delegation':
      return <ArrowRight className={`${iconClass} text-blue-400`} />;
    case 'agent_working':
      return <Bot className={`${iconClass} text-yellow-400`} />;
    case 'agent_complete':
      return success === false 
        ? <XCircle className={`${iconClass} text-red-400`} />
        : <CheckCircle2 className={`${iconClass} text-green-400`} />;
    case 'tool_call':
      return <Search className={`${iconClass} text-purple-400`} />;
    case 'scratchpad_update':
      return <FileText className={`${iconClass} text-emerald-400`} />;
    case 'system':
      return <Cpu className={`${iconClass} text-text-muted`} />;
    default:
      return <ListTodo className={`${iconClass} text-text-muted`} />;
  }
}

function getActivityStyles(type: ActivityType): string {
  switch (type) {
    case 'workflow_start':
      return 'bg-accent/10 border-l-2 border-accent';
    case 'workflow_complete':
      return 'bg-green-900/20 border-l-2 border-green-500';
    case 'workflow_error':
      return 'bg-red-900/20 border-l-2 border-red-500';
    case 'agent_delegation':
      return 'bg-blue-900/20 border-l-2 border-blue-500';
    case 'agent_working':
      return 'bg-yellow-900/10 border-l-2 border-yellow-500/50';
    case 'agent_complete':
      return 'bg-surface border-l-2 border-green-500/50';
    case 'tool_call':
      return 'bg-purple-900/10 border-l-2 border-purple-500/30';
    case 'scratchpad_update':
      return 'bg-emerald-900/10 border-l-2 border-emerald-500/30';
    case 'system':
      return 'bg-surface-light/50 border-l-2 border-text-dim';
    default:
      return 'bg-surface';
  }
}

function getActorColor(type: ActivityType): string {
  switch (type) {
    case 'workflow_start':
    case 'workflow_complete':
      return 'text-accent';
    case 'agent_delegation':
      return 'text-blue-400';
    case 'agent_working':
      return 'text-yellow-400';
    case 'agent_complete':
      return 'text-green-400';
    case 'tool_call':
      return 'text-purple-400';
    case 'scratchpad_update':
      return 'text-emerald-400';
    case 'workflow_error':
      return 'text-red-400';
    default:
      return 'text-text-muted';
  }
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
    hour12: false 
  });
}

function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

interface ActivityItemProps {
  activity: Activity;
  onNavigate?: (panel: 'plan' | 'notes' | 'draft') => void;
}

/**
 * Get the Tailwind color class for an agent based on color name.
 * We need explicit classes because Tailwind doesn't support dynamic class generation.
 */
function getAgentColorClass(colorName: string | undefined): string {
  if (!colorName) return '';
  
  const colorMap: Record<string, string> = {
    'blue': 'text-blue-400',
    'purple': 'text-purple-400',
    'orange': 'text-orange-400',
    'cyan': 'text-cyan-400',
    'green': 'text-green-400',
    'pink': 'text-pink-400',
    'yellow': 'text-yellow-400',
    'red': 'text-red-400',
  };
  
  return colorMap[colorName] || '';
}

function ActivityItem({ activity, onNavigate }: ActivityItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Determine if this activity should link to a panel
  const getNavigationPanel = (): 'plan' | 'notes' | 'draft' | null => {
    if (!onNavigate) return null;
    
    const action = activity.action.toLowerCase();
    const target = activity.target?.toLowerCase() || '';
    
    if (action.includes('task') || action.includes('plan') || target.includes('task')) {
      return 'plan';
    }
    if (action.includes('note') || target.includes('note')) {
      return 'notes';
    }
    if (action.includes('draft') || target.includes('draft')) {
      return 'draft';
    }
    return null;
  };

  const navigationPanel = getNavigationPanel();
  
  // Use agentColor if available, otherwise fall back to type-based color
  const agentColorClass = getAgentColorClass(activity.agentColor);
  const actorColorClass = agentColorClass || getActorColor(activity.type);
  
  // Check if preview text is likely truncated (rough heuristic: > 150 chars)
  const previewIsTruncatable = activity.preview && activity.preview.length > 150;
  
  return (
    <div className={`px-4 py-3 ${getActivityStyles(activity.type)} animate-slide-up`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          {getActivityIcon(activity.type, activity.success)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`font-medium text-sm ${actorColorClass}`}>
              {activity.actor}
            </span>
            <span className="text-text-dim text-xs">
              {formatTime(activity.timestamp)}
            </span>
            {activity.durationMs !== undefined && (
              <span className="text-text-dim text-xs flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDuration(activity.durationMs)}
              </span>
            )}
          </div>
          <p className="text-text text-sm leading-relaxed">
            {navigationPanel ? (
              <button
                onClick={() => onNavigate?.(navigationPanel)}
                className="text-left hover:text-accent transition-colors cursor-pointer"
              >
                {activity.action}
              </button>
            ) : (
              activity.action
            )}
          </p>
          {activity.preview && (
            <div className="mt-1.5">
              <p 
                className={`text-text-muted text-xs italic bg-surface-light/30 px-2 py-1 rounded border-l-2 border-text-dim/30 ${
                  isExpanded ? '' : 'line-clamp-2'
                } ${previewIsTruncatable ? 'cursor-pointer' : ''}`}
                onClick={previewIsTruncatable ? () => setIsExpanded(!isExpanded) : undefined}
              >
                {activity.preview}
              </p>
              {previewIsTruncatable && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-text-dim hover:text-text-muted text-xs mt-1 flex items-center gap-1 transition-colors"
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="w-3 h-3" />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-3 h-3" />
                      Show more
                    </>
                  )}
                </button>
              )}
            </div>
          )}
          {activity.details && !activity.preview && (
            <p className="text-text-muted text-xs mt-1">
              {activity.details}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function ActivityPanel({ activities, onNavigate }: ActivityPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom on new activities
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activities]);
  
  if (activities.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted">
        <Sparkles className="w-12 h-12 mb-4 opacity-50" />
        <p className="text-lg">Waiting for activity...</p>
        <p className="text-sm mt-2">Start a research session to see the workflow</p>
      </div>
    );
  }
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-border/30">
          {activities.map((activity) => (
            <ActivityItem 
              key={activity.id} 
              activity={activity} 
              onNavigate={onNavigate} 
            />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
