/**
 * Main App Component
 *
 * Entry point that handles routing between landing page and workspace.
 */

import { useState } from 'react';
import { useResearchStore } from './store';
import { QueryInput } from './components';
import { Workspace } from './views';
import { useI18n } from './i18n';
import type { DemoStateSnapshot } from './types';

function App() {
  const { session, startResearchSession, resetState, loadDemoState } = useResearchStore();
  const { language } = useI18n();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if we should show workspace or landing
  const showWorkspace = session !== null;

  const handleQuerySubmit = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      await startResearchSession(query, language);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start research session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadDemo = (snapshot: DemoStateSnapshot) => {
    setError(null);
    loadDemoState(snapshot);
  };

  const handleNewSession = () => {
    resetState();
    setError(null);
  };

  return (
    <div className="min-h-screen bg-surface-dark">
      {showWorkspace ? (
        <Workspace onNewSession={handleNewSession} />
      ) : (
        <QueryInput 
          onSubmit={handleQuerySubmit} 
          onLoadDemo={handleLoadDemo}
          isLoading={isLoading} 
          error={error} 
        />
      )}
    </div>
  );
}

export default App;
