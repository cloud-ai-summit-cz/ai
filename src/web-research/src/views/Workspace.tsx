/**
 * Research Workspace Component
 *
 * Main workspace layout with tabbed panels and live updates.
 * Updated for trace-based architecture (ADR-005).
 */

import { useResearchStore } from '../store';
import {
  Header,
  PanelTabs,
  ActivityPanel,
  PlanPanel,
  NotesPanel,
  DraftPanel,
  FinalReportPanel,
  QuestionsPanel,
} from '../components';

interface WorkspaceProps {
  onNewSession?: () => void;
}

export function Workspace({ onNewSession }: WorkspaceProps) {
  const {
    session,
    scratchpad,
    activities,
    finalReport,
    isConnected,
    activePanel,
    setActivePanel,
    showQuestionModal,
    setShowQuestionModal,
    answerQuestion,
    resetState,
  } = useResearchStore();

  const pendingQuestionsCount = scratchpad.questions.filter(q => !q.answer).length;
  const completedTasksCount = scratchpad.plan.filter(t => 
    t.status === 'completed' || t.status === 'done'
  ).length;

  const handleReset = () => {
    resetState();
    onNewSession?.();
  };

  // Navigate handler for activity panel links
  const handleNavigate = (panel: 'plan' | 'notes' | 'draft') => {
    setActivePanel(panel);
  };

  return (
    <div className="flex flex-col h-screen bg-surface-dark">
      {/* Header */}
      <Header
        query={session?.query}
        status={session?.status || 'idle'}
        isConnected={isConnected}
        onReset={handleReset}
      />

      {/* Tab Navigation */}
      <PanelTabs
        activePanel={activePanel}
        onPanelChange={setActivePanel}
        pendingQuestionsCount={pendingQuestionsCount}
        notesCount={scratchpad.notes.length}
        draftSectionsCount={scratchpad.draft.length}
        completedTasksCount={completedTasksCount}
        totalTasksCount={scratchpad.plan.length}
        hasFinalReport={finalReport !== null}
        onQuestionsClick={() => setShowQuestionModal(true)}
      />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden bg-surface">
        {activePanel === 'activity' && (
          <ActivityPanel 
            activities={activities} 
            onNavigate={handleNavigate} 
          />
        )}
        {activePanel === 'plan' && <PlanPanel tasks={scratchpad.plan} />}
        {activePanel === 'notes' && <NotesPanel notes={scratchpad.notes} />}
        {activePanel === 'draft' && <DraftPanel sections={scratchpad.draft} />}
        {activePanel === 'final' && <FinalReportPanel content={finalReport} />}
      </main>

      {/* Questions Modal */}
      {showQuestionModal && (
        <QuestionsPanel
          questions={scratchpad.questions}
          onAnswer={answerQuestion}
          isModal
          onClose={() => setShowQuestionModal(false)}
        />
      )}
    </div>
  );
}
