/**
 * Draft Panel Component
 * 
 * Displays the working document being built by agents.
 * Renders Markdown content with section navigation.
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Clock, User, ChevronRight } from 'lucide-react';
import type { DraftSection } from '../types';

interface DraftPanelProps {
  sections: DraftSection[];
}

function formatTime(timestamp?: string): string {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });
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

function SectionCard({ section, isActive, onClick }: { 
  section: DraftSection; 
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-3 border-b border-border/30
        hover:bg-surface-light/50 transition-colors
        ${isActive ? 'bg-surface-light border-l-2 border-l-accent' : ''}
      `}
    >
      <div className="flex items-center justify-between">
        <span className={`text-sm font-medium ${isActive ? 'text-accent' : 'text-text'}`}>
          {section.title}
        </span>
        <ChevronRight className={`w-4 h-4 text-text-dim ${isActive ? 'text-accent' : ''}`} />
      </div>
      <div className="flex items-center gap-3 mt-1 text-xs text-text-dim">
        {section.lastUpdatedBy && (
          <span className={`flex items-center gap-1 ${getAgentColor(section.lastUpdatedBy)}`}>
            <User className="w-3 h-3" />
            {section.lastUpdatedBy}
          </span>
        )}
        {section.lastUpdatedAt && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatTime(section.lastUpdatedAt)}
          </span>
        )}
        <span>v{section.version}</span>
      </div>
    </button>
  );
}

export function DraftPanel({ sections }: DraftPanelProps) {
  const [activeSectionId, setActiveSectionId] = useState<string | null>(
    sections.length > 0 ? sections[0].id : null
  );
  
  const activeSection = sections.find(s => s.id === activeSectionId);
  
  return (
    <div className="flex h-full">
      {/* Section Navigation */}
      <div className="w-56 border-r border-border flex-shrink-0 overflow-y-auto bg-surface-dark/50">
        <div className="p-3 border-b border-border">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-text-muted" />
            <span className="text-sm font-medium text-text">Sections</span>
          </div>
        </div>
        {sections.length === 0 ? (
          <div className="p-4 text-center text-text-muted text-sm">
            No sections yet
          </div>
        ) : (
          sections.map((section) => (
            <SectionCard
              key={section.id}
              section={section}
              isActive={section.id === activeSectionId}
              onClick={() => setActiveSectionId(section.id)}
            />
          ))
        )}
      </div>
      
      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        {activeSection ? (
          <div className="p-6">
            {/* Section Header */}
            <div className="mb-4 pb-4 border-b border-border/50">
              <h2 className="text-xl font-semibold text-text mb-2">
                {activeSection.title}
              </h2>
              <div className="flex items-center gap-4 text-xs text-text-dim">
                {activeSection.lastUpdatedBy && (
                  <span className={`flex items-center gap-1 ${getAgentColor(activeSection.lastUpdatedBy)}`}>
                    <User className="w-3 h-3" />
                    Last edited by {activeSection.lastUpdatedBy}
                  </span>
                )}
                {activeSection.lastUpdatedAt && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatTime(activeSection.lastUpdatedAt)}
                  </span>
                )}
                <span>Version {activeSection.version}</span>
              </div>
            </div>
            
            {/* Markdown Content */}
            <div className="markdown-content">
              <ReactMarkdown>
                {activeSection.content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-text-muted">
            <div className="text-center">
              <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p>No sections available</p>
              <p className="text-sm mt-1">Draft sections will appear as agents write</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
