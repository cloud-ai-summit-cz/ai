/**
 * Main App Component
 *
 * Entry point that handles routing between landing page and workspace.
 */

import { useState } from 'react';
import { useResearchStore } from './store';
import { QueryInput } from './components';
import { Workspace } from './views';

function App() {
  const { session, startResearchSession, resetState } = useResearchStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if we should show workspace or landing
  const showWorkspace = session !== null;

  const handleQuerySubmit = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      await startResearchSession(query);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start research session');
    } finally {
      setIsLoading(false);
    }
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
        <QueryInput onSubmit={handleQuerySubmit} isLoading={isLoading} error={error} />
      )}
    </div>
  );
}

export default App;
