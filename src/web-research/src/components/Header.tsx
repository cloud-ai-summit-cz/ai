/**
 * Header Component
 * 
 * Displays session info, connection status, and navigation.
 */

import { 
  Coffee, 
  Wifi, 
  WifiOff, 
  RotateCw,
  CheckCircle2,
  Loader2,
  AlertCircle
} from 'lucide-react';
import type { SessionStatus } from '../types';

interface HeaderProps {
  query?: string;
  status: SessionStatus;
  isConnected: boolean;
  onReset?: () => void;
}

function getStatusIndicator(status: SessionStatus) {
  switch (status) {
    case 'running':
      return {
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        text: 'Researching...',
        color: 'text-accent',
      };
    case 'preparing':
      return {
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        text: 'Preparing...',
        color: 'text-yellow-400',
      };
    case 'pending':
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        text: 'Pending',
        color: 'text-yellow-400',
      };
    case 'completed':
      return {
        icon: <CheckCircle2 className="w-4 h-4" />,
        text: 'Complete',
        color: 'text-green-400',
      };
    case 'failed':
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        text: 'Failed',
        color: 'text-red-400',
      };
    default:
      return {
        icon: null,
        text: '',
        color: 'text-text-muted',
      };
  }
}

export function Header({ query, status, isConnected, onReset }: HeaderProps) {
  const statusIndicator = getStatusIndicator(status);
  
  return (
    <header className="h-14 border-b border-border bg-surface-dark flex items-center justify-between px-4">
      {/* Left: Logo & Query */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Coffee className="w-6 h-6 text-accent" />
          <span className="font-semibold text-text">Cofilot</span>
        </div>
        
        {query && (
          <>
            <div className="w-px h-6 bg-border" />
            <span className="text-sm text-text-muted max-w-md truncate">
              {query}
            </span>
          </>
        )}
      </div>
      
      {/* Right: Status & Actions */}
      <div className="flex items-center gap-4">
        {/* Session Status */}
        {statusIndicator.text && (
          <div className={`flex items-center gap-2 ${statusIndicator.color}`}>
            {statusIndicator.icon}
            <span className="text-sm">{statusIndicator.text}</span>
          </div>
        )}
        
        {/* Connection Status */}
        <div className={`flex items-center gap-1.5 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
          {isConnected ? (
            <Wifi className="w-4 h-4" />
          ) : (
            <WifiOff className="w-4 h-4" />
          )}
          <span className="text-xs">{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        
        {/* Reset Button */}
        {onReset && (
          <button
            onClick={onReset}
            className="p-2 rounded hover:bg-surface-light transition-colors text-text-muted hover:text-text"
            title="New Research"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        )}
      </div>
    </header>
  );
}
