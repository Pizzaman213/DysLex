/**
 * Session Summary Component
 *
 * Displays positive session statistics with celebration styling.
 */

import { useSessionStore } from '../../stores/sessionStore';

const ENCOURAGEMENT_MESSAGES = [
  "Great work! You're making excellent progress.",
  "Nice job! Keep up the momentum.",
  "Every word is progress. Keep going!",
  "You're doing amazing! Keep writing.",
  "Fantastic effort! Your ideas are flowing.",
  "Brilliant! You're on a roll.",
  "Keep it up! You're making great strides.",
  "Excellent work! Your writing is improving.",
];

export function SessionSummary() {
  const {
    totalWordsWritten,
    correctionsApplied,
    correctionsDismissed,
    getTimeSpent,
  } = useSessionStore();

  const timeSpent = getTimeSpent();

  const getMessage = () => {
    if (totalWordsWritten === 0) {
      return "Ready to start writing? You've got this!";
    }
    const index = totalWordsWritten % ENCOURAGEMENT_MESSAGES.length;
    return ENCOURAGEMENT_MESSAGES[index];
  };

  return (
    <div
      className="session-summary"
      role="region"
      aria-label="Session summary"
    >
      <div className="session-celebration anim">
        <h3 className="session-summary-title">Session Summary</h3>
        <p className="session-summary-message">{getMessage()}</p>
      </div>

      <div className="session-summary-stats">
        <div className="session-stat">
          <span className="session-stat-value">{totalWordsWritten}</span>
          <span className="session-stat-label">Words Written</span>
        </div>

        <div className="session-stat">
          <span className="session-stat-value">{correctionsApplied}</span>
          <span className="session-stat-label">Applied</span>
        </div>

        <div className="session-stat">
          <span className="session-stat-value">{correctionsDismissed}</span>
          <span className="session-stat-label">Reviewed</span>
        </div>

        <div className="session-stat">
          <span className="session-stat-value">{timeSpent}</span>
          <span className="session-stat-label">Minutes</span>
        </div>
      </div>

      {totalWordsWritten > 0 && (
        <div className="session-next-steps">
          <h4>Next Steps</h4>
          <ul>
            <li>Review your corrections in the Suggestions tab</li>
            <li>Check readability in the Readability tab</li>
            <li>Export your polished document when ready</li>
          </ul>
        </div>
      )}
    </div>
  );
}
