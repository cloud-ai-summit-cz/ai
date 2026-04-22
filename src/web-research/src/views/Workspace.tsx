/**
 * Research Workspace Component
 *
 * Main workspace layout with tabbed panels and live updates.
 * Updated for trace-based architecture (ADR-005).
 */

import { useResearchStore } from '../store';
import { submitAnswers } from '../api';
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
    isDemoMode,
    activePanel,
    setActivePanel,
    showQuestionModal,
    setShowQuestionModal,
    answerQuestion,
    resetState,
    exportDemoState,
  } = useResearchStore();

  const pendingQuestionsCount = scratchpad.questions.filter(q => !q.answered).length;
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

  // Handle answering a question - calls API and updates local state
  const handleAnswerQuestion = async (questionId: string, answer: string) => {
    if (!session?.sessionId) return;
    
    try {
      // Update local state optimistically
      answerQuestion(questionId, answer);
      
      // Call API to submit answer (fire and forget - optimistic update already done)
      await submitAnswers(session.sessionId, [{ question_id: questionId, answer }]);
      
      // Check if there are still pending blocking questions AFTER the optimistic update
      // We need to check based on the current state excluding the just-answered question
      const remainingBlocking = scratchpad.questions.filter(
        q => !q.answered && q.priority === 'blocking' && q.id !== questionId
      );
      
      // Only close modal if no more blocking questions remain
      if (remainingBlocking.length === 0) {
        // Check if there are any other pending questions at all
        const remainingPending = scratchpad.questions.filter(
          q => !q.answered && q.id !== questionId
        );
        if (remainingPending.length === 0) {
          setShowQuestionModal(false);
        }
      }
    } catch (error) {
      console.error('Failed to submit answer:', error);
      // Could add error notification here
    }
  };

  // Save demo state handler
  const handleSaveDemo = () => {
    const snapshot = exportDemoState();
    if (!snapshot) {
      alert('Cannot save demo state: no active session');
      return;
    }
    
    // Create and download JSON file
    const json = JSON.stringify(snapshot, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cofilot-demo-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-screen bg-surface-dark">
      {/* Header */}
      <Header
        query={session?.query}
        status={session?.status || 'idle'}
        isConnected={isConnected}
        isDemoMode={isDemoMode}
        onReset={handleReset}
        onSaveDemo={handleSaveDemo}
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
          onAnswer={handleAnswerQuestion}
          isModal
          onClose={() => setShowQuestionModal(false)}
        />
      )}
    </div>
  );
}
