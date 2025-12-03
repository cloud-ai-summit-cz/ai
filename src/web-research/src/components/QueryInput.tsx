/**
 * Query Input Component
 *
 * Landing page component for entering a new research query.
 */

import { useState, useRef } from 'react';
import { Search, Sparkles, Coffee, AlertCircle, Upload, PlayCircle } from 'lucide-react';
import type { DemoStateSnapshot } from '../types';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  onLoadDemo?: (snapshot: DemoStateSnapshot) => void;
  isLoading?: boolean;
  error?: string | null;
}

const EXAMPLE_QUERIES = [
  "Should Cofilot expand to Vienna?",
  "Analyze the Berlin specialty coffee market",
  "Compare Munich vs Hamburg for new location",
];

export function QueryInput({ onSubmit, onLoadDemo, isLoading, error }: QueryInputProps) {
  const [query, setQuery] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query.trim());
    }
  };

  const handleLoadDemoClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoadError(null);

    try {
      const text = await file.text();
      const snapshot = JSON.parse(text) as DemoStateSnapshot;

      // Basic validation
      if (!snapshot.version || !snapshot.session || !snapshot.activities) {
        throw new Error('Invalid demo file format');
      }

      onLoadDemo?.(snapshot);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load demo file');
    }

    // Reset file input
    e.target.value = '';
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      {/* Logo/Brand */}
      <div className="flex items-center gap-3 mb-8">
        <Coffee className="w-10 h-10 text-accent" />
        <h1 className="text-3xl font-semibold text-text">Cofilot Research</h1>
      </div>

      {/* Tagline */}
      <p className="text-text-muted text-lg mb-12 text-center max-w-md">
        AI-powered market research for your next business move
      </p>

      {/* Error Display */}
      {(error || loadError) && (
        <div className="w-full max-w-2xl mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-red-300 text-sm">{error || loadError}</p>
        </div>
      )}

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to research?"
            disabled={isLoading}
            className="
              w-full px-6 py-4 pr-14
              bg-surface-light border border-border rounded-2xl
              text-text placeholder:text-text-dim
              focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent
              disabled:opacity-50
              text-lg
            "
          />
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="
              absolute right-3 top-1/2 -translate-y-1/2
              p-2 rounded-xl
              bg-accent hover:bg-accent-hover
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors
            "
          >
            {isLoading ? (
              <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Search className="w-6 h-6 text-white" />
            )}
          </button>
        </div>
      </form>

      {/* Example Queries */}
      <div className="mt-8">
        <p className="text-text-dim text-sm mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          Try an example:
        </p>
        <div className="flex flex-wrap gap-2 justify-center">
          {EXAMPLE_QUERIES.map((example) => (
            <button
              key={example}
              onClick={() => setQuery(example)}
              disabled={isLoading}
              className="
                px-4 py-2 rounded-full
                bg-surface-light hover:bg-surface-lighter
                border border-border hover:border-text-dim
                text-sm text-text-muted hover:text-text
                transition-colors
                disabled:opacity-50
              "
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* Demo Mode Section */}
      {onLoadDemo && (
        <div className="mt-12 pt-8 border-t border-border w-full max-w-2xl">
          <div className="flex flex-col items-center">
            <p className="text-text-dim text-sm mb-4 flex items-center gap-2">
              <PlayCircle className="w-4 h-4" />
              Or load a saved demo:
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              className="hidden"
            />
            <button
              onClick={handleLoadDemoClick}
              disabled={isLoading}
              className="
                flex items-center gap-2
                px-6 py-3 rounded-xl
                bg-purple-500/20 hover:bg-purple-500/30
                border border-purple-500/30 hover:border-purple-500/50
                text-purple-300 hover:text-purple-200
                transition-colors
                disabled:opacity-50
              "
            >
              <Upload className="w-5 h-5" />
              <span>Load Demo State</span>
            </button>
            <p className="text-text-dim text-xs mt-2">
              Load a previously saved research session
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
