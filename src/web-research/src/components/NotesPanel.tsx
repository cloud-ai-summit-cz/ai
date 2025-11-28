/**
 * Notes Panel Component
 * 
 * Displays the append-only notes/facts from the Scratchpad.
 * Each note shows the author agent and tags.
 */

import { StickyNote, Tag, User } from 'lucide-react';
import type { Note } from '../types';

interface NotesPanelProps {
  notes: Note[];
}

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

function NoteCard({ note }: { note: Note }) {
  return (
    <div className="p-4 border-b border-border/30 last:border-b-0 animate-slide-up hover:bg-surface-light/30 transition-colors">
      {/* Author & Time */}
      <div className="flex items-center justify-between mb-2">
        <div className={`flex items-center gap-2 px-2 py-1 rounded-full border text-xs ${getAgentColor(note.author)}`}>
          <User className="w-3 h-3" />
          <span>{note.author}</span>
        </div>
        <span className="text-text-dim text-xs">
          {formatTime(note.timestamp)}
        </span>
      </div>
      
      {/* Content */}
      <p className="text-sm text-text leading-relaxed mb-2">
        {note.content}
      </p>
      
      {/* Tags */}
      {note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
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
