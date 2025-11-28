/**
 * Research Workspace Component
 * 
 * Main workspace layout with tabbed panels and live updates.
 */

import { useEffect } from 'react';
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
import { createMockEventStream } from '../mocks/data';

export function Workspace() {
  const {
    session,
    scratchpad,
    messages,
    isConnected,
    activePanel,
    setActivePanel,
    showQuestionModal,
    setShowQuestionModal,
    addMessage,
    addNote,
    updateTask,
    answerQuestion,
    resetState,
  } = useResearchStore();

  // Start mock event stream for demo
  useEffect(() => {
    const cleanup = createMockEventStream((event) => {
      switch (event.type) {
        case 'message':
          addMessage(event.data as any);
          break;
        case 'note_added':
          addNote(event.data as any);
          break;
        case 'task_update':
          const taskUpdate = event.data as any;
          updateTask(taskUpdate.id, taskUpdate);
          break;
      }
    });

    return cleanup;
  }, [addMessage, addNote, updateTask]);

  const pendingQuestionsCount = scratchpad.questions.filter(q => !q.answer).length;
  const completedTasksCount = scratchpad.plan.filter(t => t.status === 'completed').length;

  return (
    <div className="flex flex-col h-screen bg-surface-dark">
      {/* Header */}
      <Header
        query={session?.query}
        status={session?.status || 'idle'}
        isConnected={isConnected}
        onReset={resetState}
      />

      {/* Tab Navigation */}
      <PanelTabs
        activePanel={activePanel}
        onPanelChange={setActivePanel}
        pendingQuestionsCount={pendingQuestionsCount}
        notesCount={scratchpad.notes.length}
        completedTasksCount={completedTasksCount}
        totalTasksCount={scratchpad.plan.length}
        onQuestionsClick={() => setShowQuestionModal(true)}
      />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden bg-surface">
        {activePanel === 'chat' && <ChatPanel messages={messages} />}
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
