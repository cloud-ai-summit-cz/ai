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
  CheckCircle2,
  Loader2
} from 'lucide-react';
import type { ChatMessage, MessageType } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
}

function getMessageIcon(type: MessageType, status?: string) {
  const iconClass = "w-4 h-4";
  
  switch (type) {
    case 'system':
      return <Cpu className={iconClass} />;
    case 'orchestrator':
      return <Bot className={iconClass} />;
    case 'agent':
      if (status === 'started') return <Loader2 className={`${iconClass} animate-spin`} />;
      if (status === 'completed') return <CheckCircle2 className={iconClass} />;
      return <Bot className={iconClass} />;
    case 'tool':
      if (status === 'started') return <Loader2 className={`${iconClass} animate-spin`} />;
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

function ChatMessageItem({ message }: { message: ChatMessage }) {
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
            {message.content}
          </p>
        </div>
      </div>
    </div>
  );
}

export function ChatPanel({ messages }: ChatPanelProps) {
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
            <ChatMessageItem key={message.id} message={message} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
