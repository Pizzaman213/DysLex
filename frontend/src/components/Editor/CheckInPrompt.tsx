/**
 * Check-In Prompt Component
 *
 * Displays empathetic support messages when frustration is detected.
 * Non-intrusive banner at top of editor with actionable next steps.
 */

import { selectMessage } from '../../utils/checkInMessages';

interface CheckInPromptProps {
  signalTypes: string[];
  onDismiss: () => void;
  onAction: (action: string) => void;
}

export function CheckInPrompt({ signalTypes, onDismiss, onAction }: CheckInPromptProps) {
  const message = selectMessage(signalTypes);

  return (
    <div
      className="check-in-prompt"
      role="status"
      aria-live="polite"
      aria-label="Writing check-in"
    >
      <div className="check-in-prompt__content">
        <span className="check-in-prompt__icon" aria-hidden="true">
          💭
        </span>
        <div className="check-in-prompt__text">
          <p className="check-in-prompt__message">{message.primary}</p>
          {message.suggestion && (
            <p className="check-in-prompt__suggestion">{message.suggestion}</p>
          )}
        </div>
      </div>

      <div className="check-in-prompt__actions">
        {message.actions?.map((action) => (
          <button
            key={action.id}
            className="check-in-prompt__action-btn"
            onClick={() => onAction(action.id)}
            type="button"
          >
            {action.label}
          </button>
        ))}
        <button
          className="check-in-prompt__dismiss"
          onClick={onDismiss}
          aria-label="Dismiss check-in"
          type="button"
        >
          ×
        </button>
      </div>
    </div>
  );
}
