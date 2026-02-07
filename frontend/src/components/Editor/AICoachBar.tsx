import { CoachNudge } from '../../hooks/useAICoach';

interface AICoachBarProps {
  nudge: CoachNudge | null;
  onDismiss: (nudgeId: string) => void;
}

export function AICoachBar({ nudge, onDismiss }: AICoachBarProps) {
  if (!nudge) return null;

  const getEmoji = (type: CoachNudge['type']) => {
    switch (type) {
      case 'section':
        return '📝';
      case 'transition':
        return '🔗';
      case 'milestone':
        return '🎯';
      case 'idle':
        return '💭';
      case 'completion':
        return '🎉';
      default:
        return '💡';
    }
  };

  return (
    <div
      className="ai-coach-bar"
      role="status"
      aria-live="polite"
      aria-label="AI writing coach"
    >
      <span className="ai-coach-bar__emoji" aria-hidden="true">
        {getEmoji(nudge.type)}
      </span>
      <span className="ai-coach-bar__message">{nudge.message}</span>
      <button
        className="ai-coach-bar__dismiss"
        onClick={() => onDismiss(nudge.id)}
        aria-label="Dismiss coaching message"
        type="button"
      >
        ×
      </button>
    </div>
  );
}
