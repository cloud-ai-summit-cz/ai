/**
 * Main App Component
 * 
 * Entry point that handles routing between landing page and workspace.
 */

import { useEffect, useState } from 'react';
import { useResearchStore } from './store';
import { QueryInput } from './components';
import { Workspace } from './views';

function App() {
  const { session, loadMockData, setSession, setConnected } = useResearchStore();
  const [isLoading, setIsLoading] = useState(false);

  // Check if we should show workspace or landing
  const showWorkspace = session !== null;

  const handleQuerySubmit = async (query: string) => {
    setIsLoading(true);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // For demo: load mock data and set session
    loadMockData();
    setIsLoading(false);
  };

  // Auto-load mock data in development for quick preview
  // Comment this out to see the landing page first
  useEffect(() => {
    // Uncomment below to auto-load mock data on startup:
    // loadMockData();
  }, []);

  return (
    <div className="min-h-screen bg-surface-dark">
      {showWorkspace ? (
        <Workspace />
      ) : (
        <QueryInput onSubmit={handleQuerySubmit} isLoading={isLoading} />
      )}
    </div>
  );
}

export default App;
