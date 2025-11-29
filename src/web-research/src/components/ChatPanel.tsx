/**
 * Chat Panel Component
 * 
 * Displays the orchestration message stream as a group chat.
 * Shows agent activities, tool calls, and status updates.
 */

import { useEffect, useRef } from 'react';
import { 
  Bot, 
  User, 
  Wrench, 
  Cpu,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import type { ChatMessage, MessageType } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  onNavigate?: (panel: 'plan' | 'notes' | 'draft') => void;
}

function getMessageIcon(type: MessageType, status?: string) {
  const iconClass = "w-4 h-4";
  
  switch (type) {
    case 'system':
      return <Cpu className={iconClass} />;
    case 'orchestrator':
      return <Bot className={iconClass} />;
    case 'agent':
      // Use static icons - no spinners in message log
      if (status === 'completed') return <CheckCircle2 className={`${iconClass} text-green-400`} />;
      return <Bot className={iconClass} />;
    case 'tool':
      // Wrench icon with color variation for status
      if (status === 'completed') return <Wrench className={`${iconClass} text-green-400`} />;
      if (status === 'started') return <Wrench className={`${iconClass} text-yellow-400`} />;
      return <Wrench className={iconClass} />;
    case 'user':
      return <User className={iconClass} />;
    case 'error':
      return <AlertCircle className={iconClass} />;
    default:
      return <Bot className={iconClass} />;
  }
}

function getMessageStyles(type: MessageType): string {
  switch (type) {
    case 'system':
      return 'bg-surface-light/50 border-l-2 border-text-dim';
    case 'orchestrator':
      return 'bg-surface-light border-l-2 border-accent';
    case 'agent':
      return 'bg-surface border-l-2 border-blue-500/50';
    case 'tool':
      return 'bg-surface-dark border-l-2 border-yellow-500/30 text-text-muted text-sm';
    case 'user':
      return 'bg-accent/10 border-l-2 border-accent';
    case 'error':
      return 'bg-red-900/20 border-l-2 border-red-500';
    default:
      return 'bg-surface';
  }
}

function getSenderColor(type: MessageType): string {
  switch (type) {
    case 'orchestrator':
      return 'text-accent';
    case 'agent':
      return 'text-blue-400';
    case 'tool':
      return 'text-yellow-400/70';
    case 'user':
      return 'text-accent';
    case 'error':
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

/**
 * Parse message content and make actionable phrases clickable.
 * E.g., "📝 Added note" becomes a link to the Notes tab.
 */
function renderMessageContent(
  content: string, 
  onNavigate?: (panel: 'plan' | 'notes' | 'draft') => void
): React.ReactNode {
  if (!onNavigate) {
    return content;
  }

  // Patterns that link to specific tabs
  const patterns: Array<{ regex: RegExp; panel: 'plan' | 'notes' | 'draft' }> = [
    { regex: /(Added \d+ tasks?|Added.*to plan)/gi, panel: 'plan' },
    { regex: /(Task updated.*|✅ Task)/gi, panel: 'plan' },
    { regex: /(Added note|📝 Added note)/gi, panel: 'notes' },
    { regex: /(Updated draft|📝 Updated draft)/gi, panel: 'draft' },
  ];

  // Find all matches and their positions
  interface Match { start: number; end: number; text: string; panel: 'plan' | 'notes' | 'draft' }
  const matches: Match[] = [];
  
  for (const { regex, panel } of patterns) {
    let match;
    const r = new RegExp(regex.source, regex.flags);
    while ((match = r.exec(content)) !== null) {
      matches.push({
        start: match.index,
        end: match.index + match[0].length,
        text: match[0],
        panel,
      });
    }
  }

  if (matches.length === 0) {
    return content;
  }

  // Sort matches by start position
  matches.sort((a, b) => a.start - b.start);

  // Build result with clickable parts
  const result: React.ReactNode[] = [];
  let lastEnd = 0;

  for (const match of matches) {
    // Add text before this match
    if (match.start > lastEnd) {
      result.push(content.slice(lastEnd, match.start));
    }
    
    // Add clickable match
    result.push(
      <button
        key={match.start}
        onClick={() => onNavigate(match.panel)}
        className="text-accent hover:text-accent-light underline underline-offset-2 cursor-pointer transition-colors"
      >
        {match.text}
      </button>
    );
    
    lastEnd = match.end;
  }

  // Add remaining text
  if (lastEnd < content.length) {
    result.push(content.slice(lastEnd));
  }

  return result;
}

interface ChatMessageItemProps {
  message: ChatMessage;
  onNavigate?: (panel: 'plan' | 'notes' | 'draft') => void;
}

function ChatMessageItem({ message, onNavigate }: ChatMessageItemProps) {
  const status = message.metadata?.status;
  
  return (
    <div className={`px-4 py-3 ${getMessageStyles(message.type)} animate-slide-up`}>
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 ${getSenderColor(message.type)}`}>
          {getMessageIcon(message.type, status)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-medium text-sm ${getSenderColor(message.type)}`}>
              {message.sender}
            </span>
            <span className="text-text-dim text-xs">
              {formatTime(message.timestamp)}
            </span>
            {message.metadata?.duration && (
              <span className="text-text-dim text-xs">
                ({(message.metadata.duration / 1000).toFixed(1)}s)
              </span>
            )}
          </div>
          <p className="text-text text-sm leading-relaxed">
            {renderMessageContent(message.content, onNavigate)}
          </p>
        </div>
      </div>
    </div>
  );
}

export function ChatPanel({ messages, onNavigate }: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="divide-y divide-border/30">
          {messages.map((message) => (
            <ChatMessageItem key={message.id} message={message} onNavigate={onNavigate} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
