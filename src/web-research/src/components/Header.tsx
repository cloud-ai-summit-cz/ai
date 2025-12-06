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
  AlertCircle,
  Download,
  PlayCircle
} from 'lucide-react';
import type { SessionStatus } from '../types';
import { useI18n } from '../i18n';

interface HeaderProps {
  query?: string;
  status: SessionStatus;
  isConnected: boolean;
  isDemoMode?: boolean;
  onReset?: () => void;
  onSaveDemo?: () => void;
}

export function Header({ query, status, isConnected, isDemoMode, onReset, onSaveDemo }: HeaderProps) {
  const { t } = useI18n();

  function getStatusIndicator(status: SessionStatus) {
    switch (status) {
      case 'running':
        return {
          icon: <Loader2 className="w-4 h-4 animate-spin" />,
          text: t.header.researching,
          color: 'text-accent',
        };
      case 'preparing':
        return {
          icon: <Loader2 className="w-4 h-4 animate-spin" />,
          text: t.header.preparing,
          color: 'text-yellow-400',
        };
      case 'pending':
        return {
          icon: <AlertCircle className="w-4 h-4" />,
          text: t.header.pending,
          color: 'text-yellow-400',
        };
      case 'completed':
        return {
          icon: <CheckCircle2 className="w-4 h-4" />,
          text: t.header.complete,
          color: 'text-green-400',
        };
      case 'failed':
        return {
          icon: <AlertCircle className="w-4 h-4" />,
          text: t.header.failed,
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

        {/* Demo Mode Badge */}
        {isDemoMode && (
          <>
            <div className="w-px h-6 bg-border" />
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-purple-500/20 border border-purple-500/30">
              <PlayCircle className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-xs text-purple-300 font-medium">{t.header.demoMode}</span>
            </div>
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
        
        {/* Connection Status (hide in demo mode) */}
        {!isDemoMode && (
          <div className={`flex items-center gap-1.5 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
            {isConnected ? (
              <Wifi className="w-4 h-4" />
            ) : (
              <WifiOff className="w-4 h-4" />
            )}
          </div>
        )}
        
        {/* Save Demo Button (show when there's an active session, not in demo mode) */}
        {onSaveDemo && !isDemoMode && (
          <button
            onClick={onSaveDemo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/20 hover:bg-accent/30 border border-accent/30 transition-colors text-accent text-sm"
            title={t.header.saveDemo}
          >
            <Download className="w-4 h-4" />
            <span>{t.header.saveDemo}</span>
          </button>
        )}
        
        {/* Reset Button */}
        {onReset && (
          <button
            onClick={onReset}
            className="p-2 rounded hover:bg-surface-light transition-colors text-text-muted hover:text-text"
            title={t.header.newResearch}
          >
            <RotateCw className="w-4 h-4" />
          </button>
        )}
      </div>
    </header>
  );
}
