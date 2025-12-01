/**
 * Research Workspace Component
 *
 * Main workspace layout with tabbed panels and live updates.
 */

import { useResearchStore } from '../store';
import {
  Header,
  PanelTabs,
  ChatPanel,
  PlanPanel,
  NotesPanel,
  DraftPanel,
  QuestionsPanel,
} from '../components';

interface WorkspaceProps {
  onNewSession?: () => void;
}

export function Workspace({ onNewSession }: WorkspaceProps) {
  const {
    session,
    scratchpad,
    messages,
    isConnected,
    activePanel,
    setActivePanel,
    showQuestionModal,
    setShowQuestionModal,
    answerQuestion,
    resetState,
  } = useResearchStore();

  const pendingQuestionsCount = scratchpad.questions.filter(q => !q.answer).length;
  const completedTasksCount = scratchpad.plan.filter(t => t.status === 'completed').length;

  const handleReset = () => {
    resetState();
    onNewSession?.();
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
        onQuestionsClick={() => setShowQuestionModal(true)}
      />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden bg-surface">
        {activePanel === 'chat' && <ChatPanel messages={messages} onNavigate={setActivePanel} />}
        {activePanel === 'plan' && <PlanPanel tasks={scratchpad.plan} />}
        {activePanel === 'notes' && <NotesPanel notes={scratchpad.notes} />}
        {activePanel === 'draft' && <DraftPanel sections={scratchpad.draft} />}
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
