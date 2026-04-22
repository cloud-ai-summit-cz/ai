/**
 * Final Report Panel Component
 * 
 * Displays the final synthesis report from the Synthesizer agent.
 * Renders full Markdown content in a clean, readable format.
 */

import ReactMarkdown from 'react-markdown';
import { FileText, CheckCircle2, Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface FinalReportPanelProps {
  content: string | null;
}

export function FinalReportPanel({ content }: FinalReportPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted">
        <div className="text-center">
          <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
          <p className="text-lg">Final Report Not Ready</p>
          <p className="text-sm mt-2">
            The final synthesis will appear here when the research is complete
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-border bg-surface-dark/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-text">Final Report</h2>
              <p className="text-xs text-text-muted">
                Synthesized research findings
              </p>
            </div>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-2 text-sm text-text-muted hover:text-text hover:bg-surface-light rounded-lg transition-colors"
            title="Copy to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-400" />
                <span className="text-green-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-4xl mx-auto">
          <div className="markdown-content prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              components={{
                // Custom heading styles
                h1: ({ children }) => (
                  <h1 className="text-2xl font-bold text-text mt-6 mb-4 pb-2 border-b border-border/50">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-xl font-semibold text-text mt-5 mb-3">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-lg font-medium text-text mt-4 mb-2">
                    {children}
                  </h3>
                ),
                // Paragraph styling
                p: ({ children }) => (
                  <p className="text-text-muted leading-relaxed mb-4">
                    {children}
                  </p>
                ),
                // List styling
                ul: ({ children }) => (
                  <ul className="list-disc list-inside text-text-muted mb-4 space-y-1">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside text-text-muted mb-4 space-y-1">
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className="text-text-muted">
                    {children}
                  </li>
                ),
                // Strong/emphasis
                strong: ({ children }) => (
                  <strong className="text-text font-semibold">
                    {children}
                  </strong>
                ),
                em: ({ children }) => (
                  <em className="text-text-muted italic">
                    {children}
                  </em>
                ),
                // Blockquote styling
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-accent/50 pl-4 my-4 text-text-muted italic">
                    {children}
                  </blockquote>
                ),
                // Code styling
                code: ({ children }) => (
                  <code className="bg-surface-light px-1.5 py-0.5 rounded text-sm text-accent">
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-surface-dark p-4 rounded-lg overflow-x-auto mb-4">
                    {children}
                  </pre>
                ),
                // Horizontal rule
                hr: () => (
                  <hr className="border-border/50 my-6" />
                ),
                // Table styling
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-4">
                    <table className="min-w-full border border-border/50 rounded">
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="px-4 py-2 bg-surface-dark text-left text-text font-semibold border-b border-border/50">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-2 text-text-muted border-b border-border/30">
                    {children}
                  </td>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
