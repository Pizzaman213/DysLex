import { useEditorStore } from '../../stores/editorStore';

interface StatusBarProps {
  onPanelToggle: (panel: 'corrections' | 'progress' | 'settings') => void;
}

export function StatusBar({ onPanelToggle }: StatusBarProps) {
  const { content, corrections, isSaving } = useEditorStore();

  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const correctionCount = corrections.length;

  return (
    <footer className="status-bar" role="contentinfo">
      <div className="status-left">
        <span className="status-item">{wordCount} words</span>
        {correctionCount > 0 && (
          <button
            className="status-item status-btn"
            onClick={() => onPanelToggle('corrections')}
            aria-label={`${correctionCount} suggestions available`}
          >
            {correctionCount} suggestions
          </button>
        )}
      </div>

      <div className="status-center">
        {isSaving && <span className="status-saving">Saving...</span>}
      </div>

      <div className="status-right">
        <button
          className="status-btn"
          onClick={() => onPanelToggle('progress')}
          aria-label="View progress"
        >
          Progress
        </button>
      </div>
    </footer>
  );
}
