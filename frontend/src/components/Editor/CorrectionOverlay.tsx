import type { Editor } from '@tiptap/react';
import type { Correction } from '../../stores/editorStore';

interface CorrectionOverlayProps {
  editor: Editor | null;
  corrections: Correction[];
}

export function CorrectionOverlay({ editor, corrections }: CorrectionOverlayProps) {
  if (!editor || corrections.length === 0) {
    return null;
  }

  return (
    <div className="correction-overlay" aria-live="polite">
      {corrections.map((correction, index) => (
        <div
          key={`${correction.start}-${correction.end}`}
          className={`correction-marker correction-${correction.type}`}
          style={{
            // Position would be calculated based on editor coordinates
          }}
          role="button"
          tabIndex={0}
          aria-label={`Suggestion: replace "${correction.original}" with "${correction.suggested}"`}
        >
          <span className="correction-original">{correction.original}</span>
          <span className="correction-arrow" aria-hidden="true">→</span>
          <span className="correction-suggested">{correction.suggested}</span>
          {correction.explanation && (
            <span className="correction-explanation">{correction.explanation}</span>
          )}
        </div>
      ))}
    </div>
  );
}
