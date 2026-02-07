/**
 * Suggestion Card Component
 *
 * Individual suggestion card with apply/dismiss actions for Polish Mode
 */

import { TrackedChange } from '../../stores/polishStore';
import { Card } from '../Shared/Card';
import { Badge } from '../Shared/Badge';

interface SuggestionCardProps {
  suggestion: TrackedChange;
  onApply: () => void;
  onDismiss: () => void;
  onClick: () => void;
  isActive?: boolean;
}

export function SuggestionCard({
  suggestion,
  onApply,
  onDismiss,
  onClick,
  isActive = false
}: SuggestionCardProps) {
  // Map category to badge variant
  const getBadgeVariant = (category: string) => {
    const variants: Record<string, any> = {
      spelling: 'spelling',
      grammar: 'grammar',
      homophone: 'homophone',
      clarity: 'clarity',
      style: 'style'
    };
    return variants[category] || 'info';
  };

  // Format change preview
  const getChangePreview = () => {
    if (suggestion.type === 'insert') {
      return (
        <span className="suggestion-preview">
          <span className="suggestion-insert">+ {suggestion.text}</span>
        </span>
      );
    } else if (suggestion.type === 'delete') {
      return (
        <span className="suggestion-preview">
          <span className="suggestion-delete">- {suggestion.original}</span>
        </span>
      );
    } else if (suggestion.type === 'replace') {
      return (
        <span className="suggestion-preview">
          <span className="suggestion-delete">{suggestion.original}</span>
          {' → '}
          <span className="suggestion-insert">{suggestion.text}</span>
        </span>
      );
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <Card
      className={`suggestion-card ${isActive ? 'suggestion-card--active' : ''}`}
      onClick={onClick}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      role="button"
      aria-label={`Suggestion: ${suggestion.category}`}
    >
      <div className="suggestion-card-header">
        <Badge variant={getBadgeVariant(suggestion.category)}>
          {suggestion.category}
        </Badge>
      </div>

      <div className="suggestion-card-preview">
        {getChangePreview()}
      </div>

      <p className="suggestion-card-explanation">
        {suggestion.explanation}
      </p>

      <div className="suggestion-card-actions">
        <button
          className="button button-primary"
          onClick={(e) => {
            e.stopPropagation();
            onApply();
          }}
          aria-label="Apply suggestion"
        >
          Apply
        </button>
        <button
          className="button button-secondary"
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          aria-label="Dismiss suggestion"
        >
          Dismiss
        </button>
      </div>
    </Card>
  );
}
