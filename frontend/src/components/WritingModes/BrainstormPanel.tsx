/**
 * BrainstormPanel — Conversation UI for the voice-to-voice brainstorm loop.
 *
 * Shows alternating user/AI chat bubbles, a state indicator, and controls
 * for auto-probe toggle, manual "Ask AI", and ending the session.
 */

import { useEffect, useRef } from 'react';
import type { LoopState } from '../../hooks/useBrainstormLoop';

interface ConversationEntry {
  role: 'user' | 'ai';
  content: string;
  timestamp: number;
}

interface BrainstormPanelProps {
  loopState: LoopState;
  conversationHistory: ConversationEntry[];
  currentUtterance: string;
  autoProbe: boolean;
  onToggleAutoProbe: (enabled: boolean) => void;
  onAskAi: () => void;
  onEndBrainstorm: () => void;
}

export function BrainstormPanel({
  loopState,
  conversationHistory,
  currentUtterance,
  autoProbe,
  onToggleAutoProbe,
  onAskAi,
  onEndBrainstorm,
}: BrainstormPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversationHistory.length, currentUtterance]);

  return (
    <div className="brainstorm-panel" role="region" aria-label="Brainstorm conversation">
      {/* Conversation bubbles */}
      <div className="brainstorm-conversation" ref={scrollRef} aria-live="polite">
        {conversationHistory.map((entry, i) => (
          <div
            key={i}
            className={`brainstorm-bubble brainstorm-bubble--${entry.role}`}
            role="log"
          >
            <span className="brainstorm-bubble__label">
              {entry.role === 'user' ? 'You' : 'AI'}
            </span>
            <p className="brainstorm-bubble__text">{entry.content}</p>
          </div>
        ))}

        {/* Show current utterance while user is speaking */}
        {loopState === 'listening' && currentUtterance && (
          <div className="brainstorm-bubble brainstorm-bubble--user brainstorm-bubble--live">
            <span className="brainstorm-bubble__label">You</span>
            <p className="brainstorm-bubble__text">{currentUtterance}</p>
          </div>
        )}
      </div>

      {/* State indicator */}
      <div className="brainstorm-state-indicator" aria-live="polite">
        {loopState === 'listening' && (
          <span className="brainstorm-state brainstorm-state--listening">
            <span className="brainstorm-dot" aria-hidden="true" />
            Listening...
          </span>
        )}
        {loopState === 'pause_detected' && (
          <span className="brainstorm-state brainstorm-state--pause">
            Processing pause...
          </span>
        )}
        {loopState === 'ai_thinking' && (
          <span className="brainstorm-state brainstorm-state--thinking">
            <span className="brainstorm-spinner" aria-hidden="true" />
            Thinking...
          </span>
        )}
        {loopState === 'ai_speaking' && (
          <span className="brainstorm-state brainstorm-state--speaking">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
            Speaking...
          </span>
        )}
        {loopState === 'waiting_manual' && (
          <span className="brainstorm-state brainstorm-state--waiting">
            Press "Ask AI" when ready
          </span>
        )}
      </div>

      {/* Controls */}
      <div className="brainstorm-controls">
        <label className="brainstorm-toggle" htmlFor="brainstorm-auto-probe">
          <input
            id="brainstorm-auto-probe"
            type="checkbox"
            checked={autoProbe}
            onChange={(e) => onToggleAutoProbe(e.target.checked)}
          />
          <span className="brainstorm-toggle__slider" />
          <span className="brainstorm-toggle__label">Auto-probe</span>
        </label>

        <button
          className={`btn btn-secondary brainstorm-ask-btn ${!autoProbe ? 'brainstorm-ask-btn--primary' : ''}`}
          onClick={onAskAi}
          disabled={
            loopState === 'ai_thinking' ||
            loopState === 'ai_speaking' ||
            loopState === 'idle'
          }
          aria-label="Ask AI to respond"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Ask AI
        </button>

        <button
          className="btn btn-ghost brainstorm-end-btn"
          onClick={onEndBrainstorm}
          aria-label="End brainstorm session"
        >
          End Brainstorm
        </button>
      </div>
    </div>
  );
}
