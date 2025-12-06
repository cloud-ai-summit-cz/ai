/**
 * Panel Tabs Component
 * 
 * Navigation tabs for switching between workspace panels.
 */

import { 
  Activity, 
  ListTodo, 
  StickyNote, 
  FileText,
  HelpCircle,
  CheckCircle2
} from 'lucide-react';
import { useI18n } from '../i18n';

type PanelType = 'activity' | 'plan' | 'notes' | 'draft' | 'final';

interface PanelTabsProps {
  activePanel: PanelType;
  onPanelChange: (panel: PanelType) => void;
  pendingQuestionsCount: number;
  notesCount: number;
  draftSectionsCount: number;
  completedTasksCount: number;
  totalTasksCount: number;
  hasFinalReport: boolean;
  onQuestionsClick: () => void;
}

export function PanelTabs({
  activePanel,
  onPanelChange,
  pendingQuestionsCount,
  notesCount,
  draftSectionsCount,
  completedTasksCount,
  totalTasksCount,
  hasFinalReport,
  onQuestionsClick,
}: PanelTabsProps) {
  const { t } = useI18n();

  interface TabConfig {
    id: PanelType;
    label: string;
    icon: React.ReactNode;
    badge?: string | number;
    highlight?: boolean;
  }

  const tabs: TabConfig[] = [
    {
      id: 'activity',
      label: t.panels.activity,
      icon: <Activity className="w-4 h-4" />,
    },
    {
      id: 'plan',
      label: t.panels.plan,
      icon: <ListTodo className="w-4 h-4" />,
      badge: totalTasksCount > 0 ? `${completedTasksCount}/${totalTasksCount}` : undefined,
    },
    {
      id: 'notes',
      label: t.panels.notes,
      icon: <StickyNote className="w-4 h-4" />,
      badge: notesCount > 0 ? notesCount : undefined,
    },
    {
      id: 'draft',
      label: t.panels.draft,
      icon: <FileText className="w-4 h-4" />,
      badge: draftSectionsCount > 0 ? draftSectionsCount : undefined,
    },
    {
      id: 'final',
      label: t.panels.finalReport,
      icon: <CheckCircle2 className="w-4 h-4" />,
      highlight: hasFinalReport,
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
              : tab.highlight
                ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
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
        <span>{t.questions.title}</span>
        {pendingQuestionsCount > 0 && (
          <span className="px-1.5 py-0.5 rounded-full bg-yellow-500 text-black text-xs font-bold">
            {pendingQuestionsCount}
          </span>
        )}
      </button>
    </div>
  );
}
