import { Correction } from '../../stores/editorStore';
import { Tooltip } from '../Shared/Tooltip';
import { Badge } from '../Shared/Badge';

interface CorrectionTooltipProps {
  correction: Correction | null;
  anchorRect: DOMRect | null;
  isOpen: boolean;
  onClose: () => void;
  onApply: () => void;
  onDismiss: () => void;
}

export function CorrectionTooltip({
  correction,
  anchorRect,
  isOpen,
  onClose,
  onApply,
  onDismiss,
}: CorrectionTooltipProps) {
  if (!correction) return null;

  // Expanded label mapping to cover granular dyslexic error types — Connor S., Feb 8
  const getCorrectionLabel = (type: Correction['type']) => {
    switch (type) {
      case 'omission':
        return 'Missing Letter';
      case 'insertion':
        return 'Extra Letter';
      case 'transposition':
        return 'Swapped Letters';
      case 'substitution':
        return 'Wrong Letter';
      case 'spelling':
        return 'Spelling';
      case 'grammar':
        return 'Grammar';
      case 'confusion':
        return 'Word Choice';
      case 'phonetic':
        return 'Phonetic';
      case 'homophone':
        return 'Homophone';
      case 'clarity':
        return 'Clarity';
      case 'style':
        return 'Style';
      default:
        return 'Suggestion';
    }
  };

  return (
    <Tooltip isOpen={isOpen} anchorRect={anchorRect} onClose={onClose}>
      <div className="correction-tooltip">
        <div className="correction-tooltip__header">
          <Badge variant={correction.type as any}>
            {getCorrectionLabel(correction.type)}
          </Badge>
        </div>

        <div className="correction-tooltip__change">
          <span className="correction-tooltip__original">{correction.original}</span>
          <span className="correction-tooltip__arrow">→</span>
          <span className="correction-tooltip__suggested">{correction.suggested}</span>
        </div>

        {correction.explanation && (
          <p className="correction-tooltip__explanation">{correction.explanation}</p>
        )}

        <div className="correction-tooltip__actions">
          <button
            className="correction-tooltip__btn correction-tooltip__btn--apply"
            onClick={onApply}
            type="button"
          >
            Apply
          </button>
          <button
            className="correction-tooltip__btn correction-tooltip__btn--dismiss"
            onClick={onDismiss}
            type="button"
          >
            Dismiss
          </button>
        </div>
      </div>
    </Tooltip>
  );
}
