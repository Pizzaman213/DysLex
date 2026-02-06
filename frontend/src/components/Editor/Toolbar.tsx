import { VoiceBar } from '../Shared/VoiceBar';

interface ToolbarProps {
  mode: 'capture' | 'mindmap' | 'draft' | 'polish';
}

export function Toolbar({ mode }: ToolbarProps) {
  return (
    <div className="toolbar" role="toolbar" aria-label="Editor toolbar">
      {mode === 'capture' && <VoiceBar />}

      {(mode === 'draft' || mode === 'polish') && (
        <div className="format-tools">
          <button
            className="toolbar-btn"
            aria-label="Bold"
            title="Bold (Ctrl+B)"
          >
            <strong>B</strong>
          </button>
          <button
            className="toolbar-btn"
            aria-label="Italic"
            title="Italic (Ctrl+I)"
          >
            <em>I</em>
          </button>
          <button
            className="toolbar-btn"
            aria-label="Heading"
            title="Heading"
          >
            H
          </button>
          <button
            className="toolbar-btn"
            aria-label="List"
            title="Bullet list"
          >
            •
          </button>
        </div>
      )}

      {mode === 'polish' && (
        <div className="polish-tools">
          <button
            className="toolbar-btn"
            aria-label="Read aloud"
            title="Read text aloud"
          >
            🔊
          </button>
          <button
            className="toolbar-btn"
            aria-label="Check grammar"
            title="Run grammar check"
          >
            ✓
          </button>
        </div>
      )}
    </div>
  );
}
