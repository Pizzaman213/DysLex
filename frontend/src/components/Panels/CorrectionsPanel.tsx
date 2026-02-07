import { Editor } from '@tiptap/react';
import { useEditorStore, Correction } from '../../stores/editorStore';
import { useSessionStore } from '../../stores/sessionStore';
import { Card } from '../Shared/Card';
import { Badge } from '../Shared/Badge';

interface CorrectionsPanelProps {
  editor: Editor | null;
}

export function CorrectionsPanel({ editor }: CorrectionsPanelProps) {
  const { corrections, applyCorrection, dismissCorrection, applyAllCorrections, setActiveCorrection } =
    useEditorStore();
  const { recordCorrectionApplied, recordCorrectionDismissed } = useSessionStore();

  // Filter out applied/dismissed corrections
  const activeCorrections = corrections.filter(
    (c) => !c.isApplied && !c.isDismissed
  );

  // Sort by position in document
  const sortedCorrections = [...activeCorrections].sort((a, b) => a.start - b.start);

  const handleApply = (correction: Correction) => {
    if (!editor) return;

    // Replace text in editor
    editor
      .chain()
      .focus()
      .insertContentAt({ from: correction.start, to: correction.end }, correction.suggested)
      .run();

    // Mark as applied
    applyCorrection(correction.id);

    // Track in session
    recordCorrectionApplied();
  };

  const handleDismiss = (correction: Correction) => {
    dismissCorrection(correction.id);

    // Track in session
    recordCorrectionDismissed();
  };

  const handleApplyAll = () => {
    if (!editor) return;

    // Apply in reverse order to avoid position shifts
    const reversedCorrections = [...sortedCorrections].reverse();

    reversedCorrections.forEach((correction) => {
      editor
        .chain()
        .insertContentAt(
          { from: correction.start, to: correction.end },
          correction.suggested
        )
        .run();

      // Track each correction
      recordCorrectionApplied();
    });

    // Mark all as applied
    applyAllCorrections();
  };

  const handleCardClick = (correction: Correction) => {
    if (!editor) return;

    // Scroll to and highlight the correction in editor
    editor.chain().focus().setTextSelection(correction.start).scrollIntoView().run();

    // Set as active correction
    setActiveCorrection(correction.id);
  };

  if (sortedCorrections.length === 0) {
    return (
      <div className="corrections-panel" role="region" aria-label="Corrections panel">
        <h2 className="corrections-panel__title">Suggestions</h2>
        <p className="corrections-panel__empty">No suggestions right now. Keep writing!</p>
      </div>
    );
  }

  return (
    <div className="corrections-panel" role="region" aria-label="Corrections panel">
      <div className="corrections-panel__header">
        <h2 className="corrections-panel__title">Suggestions</h2>
        {sortedCorrections.length > 1 && (
          <button
            className="corrections-panel__apply-all"
            onClick={handleApplyAll}
            type="button"
          >
            Apply All ({sortedCorrections.length})
          </button>
        )}
      </div>

      <div className="corrections-panel__list">
        {sortedCorrections.map((correction) => (
          <Card
            key={correction.id}
            className="correction-card"
            onClick={() => handleCardClick(correction)}
            tabIndex={0}
            role="button"
            aria-label={`Correction: ${correction.original} to ${correction.suggested}`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleCardClick(correction);
              }
            }}
          >
            <div className="correction-card__header">
              <Badge variant={correction.type as any}>
                {getCorrectionLabel(correction.type)}
              </Badge>
            </div>

            <div className="correction-card__change">
              <span className="correction-card__original">{correction.original}</span>
              <span className="correction-card__arrow" aria-hidden="true">
                →
              </span>
              <span className="correction-card__suggested">{correction.suggested}</span>
            </div>

            {correction.explanation && (
              <p className="correction-card__explanation">{correction.explanation}</p>
            )}

            <div className="correction-card__actions">
              <button
                className="correction-card__btn correction-card__btn--apply"
                onClick={(e) => {
                  e.stopPropagation();
                  handleApply(correction);
                }}
                type="button"
              >
                Apply
              </button>
              <button
                className="correction-card__btn correction-card__btn--dismiss"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDismiss(correction);
                }}
                type="button"
              >
                Dismiss
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function getCorrectionLabel(type: Correction['type']): string {
  switch (type) {
    case 'spelling':
      return 'Spelling';
    case 'grammar':
      return 'Grammar';
    case 'confusion':
      return 'Word Choice';
    case 'phonetic':
      return 'Sound-alike';
    case 'homophone':
      return 'Homophone';
    case 'clarity':
      return 'Clarity';
    case 'style':
      return 'Style';
    default:
      return 'Suggestion';
  }
}
