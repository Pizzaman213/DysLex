import { useEditorStore } from '../../stores/editorStore';

export function CorrectionsPanel() {
  const { corrections } = useEditorStore();

  if (corrections.length === 0) {
    return (
      <div className="corrections-panel" role="region" aria-label="Corrections panel">
        <h2>Suggestions</h2>
        <p className="empty-state">No suggestions right now. Keep writing!</p>
      </div>
    );
  }

  return (
    <div className="corrections-panel" role="region" aria-label="Corrections panel">
      <h2>Suggestions</h2>
      <ul className="corrections-list">
        {corrections.map((correction, index) => (
          <li key={`${correction.start}-${correction.end}`} className="correction-item">
            <div className="correction-header">
              <span className={`correction-badge correction-${correction.type}`}>
                {getCorrectionLabel(correction.type)}
              </span>
            </div>
            <div className="correction-content">
              <span className="correction-original">{correction.original}</span>
              <span className="correction-arrow" aria-hidden="true">→</span>
              <span className="correction-suggested">{correction.suggested}</span>
            </div>
            {correction.explanation && (
              <p className="correction-explanation">{correction.explanation}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function getCorrectionLabel(type: string): string {
  switch (type) {
    case 'spelling':
      return 'Spelling';
    case 'grammar':
      return 'Grammar';
    case 'confusion':
      return 'Word Choice';
    case 'phonetic':
      return 'Sound-alike';
    default:
      return 'Suggestion';
  }
}
