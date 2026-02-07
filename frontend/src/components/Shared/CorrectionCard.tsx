import { Badge } from './Badge';
import { Card } from './Card';

interface CorrectionCardProps {
  original: string;
  correction: string;
  errorType: 'spelling' | 'grammar' | 'homophone' | 'clarity' | 'style';
  explanation: string;
  onApply: () => void;
  onDismiss: () => void;
  isActive?: boolean;
}

export function CorrectionCard({
  original,
  correction,
  errorType,
  explanation,
  onApply,
  onDismiss,
  isActive = false
}: CorrectionCardProps) {
  return (
    <Card className={`correction-card ${isActive ? 'correction-card--active' : ''}`}>
      <div className="correction-card-header">
        <Badge variant={errorType}>{errorType}</Badge>
      </div>

      <div className="correction-card-preview">
        <span className="correction-original">{original}</span>
        <span className="correction-arrow"> → </span>
        <span className="correction-suggested">{correction}</span>
      </div>

      <p className="correction-explanation">{explanation}</p>

      <div className="correction-card-actions">
        <button
          className="button button-primary"
          onClick={onApply}
          aria-label={`Apply correction: change ${original} to ${correction}`}
        >
          Apply
        </button>
        <button
          className="button button-secondary"
          onClick={onDismiss}
          aria-label="Dismiss this suggestion"
        >
          Dismiss
        </button>
      </div>
    </Card>
  );
}
