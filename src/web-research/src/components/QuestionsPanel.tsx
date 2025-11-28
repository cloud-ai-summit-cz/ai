/**
 * Questions Panel Component
 * 
 * Displays pending questions from agents and allows user to answer.
 * Can be shown as a modal or inline panel.
 */

import { useState } from 'react';
import { 
  HelpCircle, 
  AlertCircle, 
  CheckCircle2, 
  Send,
  X 
} from 'lucide-react';
import type { Question } from '../types';

interface QuestionsPanelProps {
  questions: Question[];
  onAnswer: (questionId: string, answer: string) => void;
  isModal?: boolean;
  onClose?: () => void;
}

function getPriorityStyle(priority: Question['priority']): string {
  switch (priority) {
    case 'high':
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'low':
    default:
      return 'bg-text-dim/20 text-text-muted border-border';
  }
}

function getAgentColor(agent: string): string {
  switch (agent) {
    case 'market-analyst':
      return 'text-blue-400';
    case 'competitor-analyst':
      return 'text-purple-400';
    case 'location-scout':
      return 'text-orange-400';
    case 'finance-analyst':
      return 'text-green-400';
    case 'synthesizer':
      return 'text-accent';
    default:
      return 'text-text-muted';
  }
}

function QuestionCard({ 
  question, 
  onAnswer 
}: { 
  question: Question; 
  onAnswer: (answer: string) => void;
}) {
  const [inputValue, setInputValue] = useState('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  
  const handleSubmit = () => {
    const answer = question.options ? selectedOption : inputValue;
    if (answer) {
      onAnswer(answer);
      setInputValue('');
      setSelectedOption(null);
    }
  };
  
  const isAnswered = !!question.answer;
  
  return (
    <div 
      className={`
        p-4 border border-border rounded-lg mb-4 last:mb-0
        ${question.blocking && !isAnswered ? 'border-red-500/50 bg-red-500/5' : 'bg-surface-light/30'}
        ${isAnswered ? 'opacity-60' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {question.blocking ? (
            <AlertCircle className="w-5 h-5 text-red-400" />
          ) : (
            <HelpCircle className="w-5 h-5 text-yellow-400" />
          )}
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${getPriorityStyle(question.priority)}`}>
            {question.priority}
          </span>
          {question.blocking && (
            <span className="text-xs text-red-400 font-medium">Blocking</span>
          )}
        </div>
        <span className={`text-xs ${getAgentColor(question.askedBy)}`}>
          from {question.askedBy}
        </span>
      </div>
      
      {/* Question */}
      <p className="text-text font-medium mb-2">{question.text}</p>
      
      {question.context && (
        <p className="text-sm text-text-muted mb-4 italic">
          {question.context}
        </p>
      )}
      
      {/* Answer Section */}
      {isAnswered ? (
        <div className="flex items-center gap-2 p-3 bg-green-500/10 rounded border border-green-500/30">
          <CheckCircle2 className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-400">Answered: {question.answer}</span>
        </div>
      ) : question.options ? (
        <div className="space-y-2">
          {question.options.map((option) => (
            <button
              key={option}
              onClick={() => setSelectedOption(option)}
              className={`
                w-full text-left px-4 py-2 rounded border transition-colors
                ${selectedOption === option 
                  ? 'bg-accent/20 border-accent text-accent' 
                  : 'bg-surface-dark border-border hover:border-text-dim text-text'
                }
              `}
            >
              {option}
            </button>
          ))}
          {selectedOption && (
            <button
              onClick={handleSubmit}
              className="w-full mt-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />
              Submit Answer
            </button>
          )}
        </div>
      ) : (
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Type your answer..."
            className="flex-1 px-4 py-2 bg-surface-dark border border-border rounded text-text placeholder:text-text-dim focus:outline-none focus:border-accent"
          />
          <button
            onClick={handleSubmit}
            disabled={!inputValue}
            className="px-4 py-2 bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white rounded transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export function QuestionsPanel({ questions, onAnswer, isModal, onClose }: QuestionsPanelProps) {
  const pendingQuestions = questions.filter(q => !q.answer);
  const answeredQuestions = questions.filter(q => q.answer);
  const hasBlockingQuestions = pendingQuestions.some(q => q.blocking);
  
  const content = (
    <>
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-text-muted" />
          <span className="text-sm font-medium text-text">Questions</span>
          {pendingQuestions.length > 0 && (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              hasBlockingQuestions ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
            }`}>
              {pendingQuestions.length} pending
            </span>
          )}
        </div>
        {isModal && onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-surface-light rounded transition-colors"
          >
            <X className="w-5 h-5 text-text-muted" />
          </button>
        )}
      </div>
      
      {/* Questions List */}
      <div className="flex-1 overflow-y-auto p-4">
        {questions.length === 0 ? (
          <div className="text-center text-text-muted py-8">
            <HelpCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No questions yet</p>
            <p className="text-sm mt-1">Agents may ask for input during research</p>
          </div>
        ) : (
          <>
            {pendingQuestions.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-text-muted mb-3">Pending Questions</h3>
                {pendingQuestions.map((question) => (
                  <QuestionCard
                    key={question.id}
                    question={question}
                    onAnswer={(answer) => onAnswer(question.id, answer)}
                  />
                ))}
              </div>
            )}
            {answeredQuestions.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-text-dim mb-3">Answered</h3>
                {answeredQuestions.map((question) => (
                  <QuestionCard
                    key={question.id}
                    question={question}
                    onAnswer={() => {}}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
  
  if (isModal) {
    return (
      <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
        <div className="bg-surface border border-border rounded-lg shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col animate-fade-in">
          {content}
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex flex-col h-full">
      {content}
    </div>
  );
}
