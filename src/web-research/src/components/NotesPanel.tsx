/**
 * Notes Panel Component
 * 
 * Displays the append-only notes/facts from the Scratchpad.
 * Each note shows the author agent and tags.
 * Notes can be collapsed/expanded and are rendered as Markdown.
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { StickyNote, Tag, User, ChevronDown, ChevronRight } from 'lucide-react';
import type { Note } from '../types';

interface NotesPanelProps {
  notes: Note[];
}

// Number of characters to show before truncating
const TRUNCATE_LENGTH = 300;
// Number of lines to show before truncating (as fallback)
const TRUNCATE_LINES = 4;

function getAgentColor(agent: string): string {
  switch (agent) {
    case 'market-analyst':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    case 'competitor-analyst':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
    case 'location-scout':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'finance-analyst':
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'synthesizer':
      return 'bg-accent/20 text-accent border-accent/30';
    default:
      return 'bg-surface-lighter text-text-muted border-border';
  }
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });
}

/**
 * Check if content should be truncated.
 */
function shouldTruncate(content: string): boolean {
  const lineCount = content.split('\n').length;
  return content.length > TRUNCATE_LENGTH || lineCount > TRUNCATE_LINES;
}

/**
 * Get truncated content for preview.
 */
function getTruncatedContent(content: string): string {
  const lines = content.split('\n');
  
  // If within line limit, truncate by character
  if (lines.length <= TRUNCATE_LINES) {
    if (content.length <= TRUNCATE_LENGTH) {
      return content;
    }
    return content.slice(0, TRUNCATE_LENGTH) + '...';
  }
  
  // Otherwise, truncate by lines
  const truncatedLines = lines.slice(0, TRUNCATE_LINES);
  let result = truncatedLines.join('\n');
  
  // Also apply character limit to the truncated lines
  if (result.length > TRUNCATE_LENGTH) {
    result = result.slice(0, TRUNCATE_LENGTH);
  }
  
  return result + '...';
}

function NoteCard({ note }: { note: Note }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const needsTruncation = shouldTruncate(note.content);
  
  const displayContent = needsTruncation && !isExpanded 
    ? getTruncatedContent(note.content) 
    : note.content;
  
  return (
    <div 
      className={`p-4 border-b border-border/30 last:border-b-0 animate-slide-up transition-colors ${
        needsTruncation ? 'cursor-pointer hover:bg-surface-light/30' : 'hover:bg-surface-light/20'
      }`}
      onClick={() => needsTruncation && setIsExpanded(!isExpanded)}
    >
      {/* Author & Time */}
      <div className="flex items-center justify-between mb-2">
        <div className={`flex items-center gap-2 px-2 py-1 rounded-full border text-xs ${getAgentColor(note.author)}`}>
          <User className="w-3 h-3" />
          <span>{note.author}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-text-dim text-xs">
            {formatTime(note.timestamp)}
          </span>
          {needsTruncation && (
            <button 
              className="text-text-muted hover:text-text transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              aria-label={isExpanded ? 'Collapse note' : 'Expand note'}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>
      
      {/* Content - Rendered as Markdown */}
      <div className={`text-sm text-text leading-relaxed mb-2 markdown-content note-content ${
        !isExpanded && needsTruncation ? 'line-clamp-none' : ''
      }`}>
        <ReactMarkdown>
          {displayContent}
        </ReactMarkdown>
      </div>
      
      {/* Expand indicator */}
      {needsTruncation && !isExpanded && (
        <div className="text-xs text-accent hover:text-accent-light cursor-pointer mt-1">
          Click to expand...
        </div>
      )}
      
      {/* Tags */}
      {note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {note.tags.map((tag) => (
            <span 
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-surface-dark rounded text-xs text-text-muted"
            >
              <Tag className="w-3 h-3" />
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function NotesPanel({ notes }: NotesPanelProps) {
  // Show newest first
  const sortedNotes = [...notes].reverse();
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StickyNote className="w-4 h-4 text-text-muted" />
            <span className="text-sm font-medium text-text">Research Notes</span>
          </div>
          <span className="text-sm text-text-muted">
            {notes.length} notes
          </span>
        </div>
        <p className="text-xs text-text-dim mt-1">
          Raw facts and findings shared by agents
        </p>
      </div>
      
      {/* Notes List */}
      <div className="flex-1 overflow-y-auto">
        {sortedNotes.length === 0 ? (
          <div className="p-8 text-center text-text-muted">
            <StickyNote className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No notes yet</p>
            <p className="text-sm mt-1">Agents will add notes as they research</p>
          </div>
        ) : (
          sortedNotes.map((note) => (
            <NoteCard key={note.id} note={note} />
          ))
        )}
      </div>
    </div>
  );
}
