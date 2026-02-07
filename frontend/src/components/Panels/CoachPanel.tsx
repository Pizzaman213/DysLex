import { useState, useRef, useEffect, useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { useCoachStore } from '../../stores/coachStore';
import { useCoachChat } from '../../hooks/useCoachChat';

interface CoachPanelProps {
  editor: Editor | null;
}

const STARTERS = [
  "How's my writing going?",
  'Help me get unstuck',
  'What should I work on next?',
  'Can you explain a correction?',
];

export function CoachPanel({ editor }: CoachPanelProps) {
  const { messages, isLoading } = useCoachStore();
  const { sendMessage } = useCoachChat(editor);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    sendMessage(text);
  }, [input, isLoading, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  // Empty state — welcome + starters
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="coach-panel" role="region" aria-label="AI Coach">
        <div className="coach-panel__welcome">
          <p className="coach-panel__welcome-title">Your Writing Coach</p>
          <p className="coach-panel__welcome-body">
            Ask me anything about your writing — I'm here to help you get your ideas across.
          </p>
        </div>

        <div className="coach-panel__starters">
          {STARTERS.map((starter) => (
            <button
              key={starter}
              className="coach-panel__starter-btn"
              type="button"
              onClick={() => sendMessage(starter)}
            >
              {starter}
            </button>
          ))}
        </div>

        <div className="coach-panel__input-area">
          <textarea
            className="coach-panel__input"
            placeholder="Ask your coach..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          />
          <button
            className="coach-panel__send-btn"
            type="button"
            onClick={handleSend}
            disabled={!input.trim()}
            aria-label="Send message"
          >
            Send
          </button>
        </div>
      </div>
    );
  }

  // Chat state — messages + input
  return (
    <div className="coach-panel" role="region" aria-label="AI Coach">
      <div className="coach-panel__messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`coach-message coach-message--${msg.role}`}
          >
            <p className="coach-message__content">{msg.content}</p>
          </div>
        ))}

        {isLoading && (
          <div className="coach-message coach-message--coach">
            <div className="coach-typing-indicator">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="coach-panel__input-area">
        <textarea
          className="coach-panel__input"
          placeholder="Ask your coach..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
        />
        <button
          className="coach-panel__send-btn"
          type="button"
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          aria-label="Send message"
        >
          Send
        </button>
      </div>
    </div>
  );
}
