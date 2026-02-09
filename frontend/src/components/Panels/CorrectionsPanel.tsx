import { Editor } from '@tiptap/react';
import { useEditorStore, Correction } from '../../stores/editorStore';
import { useSessionStore } from '../../stores/sessionStore';
import { Card } from '../Shared/Card';
import { Badge } from '../Shared/Badge';

/**
 * Find `original` text in the ProseMirror document and replace it with `replacement`.
 * Searches the document text nodes directly — no position mapping needed.
 * Returns true if the replacement was applied.
 */
function findAndReplace(editor: Editor, original: string, replacement: string): boolean {
  const { doc } = editor.state;
  let applied = false;

  doc.descendants((node, pos) => {
    if (applied) return false;
    if (node.isText && node.text) {
      const idx = node.text.indexOf(original);
      if (idx !== -1) {
        const from = pos + idx;
        const to = from + original.length;
        editor.chain().focus()
          .insertContentAt({ from, to }, replacement)
          .run();
        applied = true;
        return false;
      }
    }
    return true;
  });

  return applied;
}

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

    // Search for the original text in the document and replace it.
    // This is more robust than using mapped positions which can drift.
    findAndReplace(editor, correction.original, correction.suggested);

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

    // Apply each correction by searching for its text.
    // Apply in reverse document order so earlier replacements don't shift later ones.
    const reversedCorrections = [...sortedCorrections].reverse();

    reversedCorrections.forEach((correction) => {
      findAndReplace(editor, correction.original, correction.suggested);
      recordCorrectionApplied();
    });

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
        <p className="corrections-panel__empty">Looking good! No suggestions right now — keep going!</p>
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

// Added fine-grained error types for dyslexic patterns (connor, feb 8)
function getCorrectionLabel(type: string): string {
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
      return 'Quick Fix';
    case 'grammar':
    case 'subject_verb':
    case 'tense':
    case 'article':
    case 'word_order':
    case 'missing_word':
    case 'run_on':
      return 'Polish';
    case 'homophone':
    case 'phonetic':
      return 'Sound-alike';
    case 'confusion':
    case 'word_choice':
      return 'Word Swap';
    case 'clarity':
      return 'Clarity Boost';
    case 'style':
      return 'Style Tip';
    default:
      return 'Suggestion';
  }
}
