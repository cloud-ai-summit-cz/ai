/**
 * Panel Tabs Component
 * 
 * Navigation tabs for switching between workspace panels.
 */

import { 
  MessageSquare, 
  ListTodo, 
  StickyNote, 
  FileText,
  HelpCircle
} from 'lucide-react';

type PanelType = 'chat' | 'plan' | 'notes' | 'draft';

interface PanelTabsProps {
  activePanel: PanelType;
  onPanelChange: (panel: PanelType) => void;
  pendingQuestionsCount: number;
  notesCount: number;
  draftSectionsCount: number;
  completedTasksCount: number;
  totalTasksCount: number;
  onQuestionsClick: () => void;
}

interface TabConfig {
  id: PanelType;
  label: string;
  icon: React.ReactNode;
  badge?: string | number;
}

export function PanelTabs({
  activePanel,
  onPanelChange,
  pendingQuestionsCount,
  notesCount,
  draftSectionsCount,
  completedTasksCount,
  totalTasksCount,
  onQuestionsClick,
}: PanelTabsProps) {
  const tabs: TabConfig[] = [
    {
      id: 'chat',
      label: 'Activity',
      icon: <MessageSquare className="w-4 h-4" />,
    },
    {
      id: 'plan',
      label: 'Plan',
      icon: <ListTodo className="w-4 h-4" />,
      badge: totalTasksCount > 0 ? `${completedTasksCount}/${totalTasksCount}` : undefined,
    },
    {
      id: 'notes',
      label: 'Notes',
      icon: <StickyNote className="w-4 h-4" />,
      badge: notesCount > 0 ? notesCount : undefined,
    },
    {
      id: 'draft',
      label: 'Draft',
      icon: <FileText className="w-4 h-4" />,
      badge: draftSectionsCount > 0 ? draftSectionsCount : undefined,
    },
  ];

  return (
    <div className="h-12 border-b border-border bg-surface flex items-center px-2 gap-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onPanelChange(tab.id)}
          className={`
            flex items-center gap-2 px-4 py-2 rounded-lg
            transition-colors text-sm font-medium
            ${activePanel === tab.id
              ? 'bg-surface-light text-text'
              : 'text-text-muted hover:text-text hover:bg-surface-light/50'
            }
          `}
        >
          {tab.icon}
          <span>{tab.label}</span>
          {tab.badge !== undefined && (
            <span className="px-1.5 py-0.5 rounded bg-surface-lighter text-xs text-text-muted">
              {tab.badge}
            </span>
          )}
        </button>
      ))}
      
      {/* Questions Button (separate, with alert styling) */}
      <div className="flex-1" />
      <button
        onClick={onQuestionsClick}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg
          transition-colors text-sm font-medium
          ${pendingQuestionsCount > 0
            ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
            : 'text-text-muted hover:text-text hover:bg-surface-light/50'
          }
        `}
      >
        <HelpCircle className="w-4 h-4" />
        <span>Questions</span>
        {pendingQuestionsCount > 0 && (
          <span className="px-1.5 py-0.5 rounded-full bg-yellow-500 text-black text-xs font-bold">
            {pendingQuestionsCount}
          </span>
        )}
      </button>
    </div>
  );
}
