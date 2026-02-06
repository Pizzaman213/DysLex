import { useState } from 'react';
import { Editor } from '../Editor/Editor';
import { useTextToSpeech } from '../../hooks/useTextToSpeech';
import { useEditorStore } from '../../stores/editorStore';

export function PolishMode() {
  const { content, corrections } = useEditorStore();
  const { speak, stop, isSpeaking } = useTextToSpeech();
  const [showStats, setShowStats] = useState(false);

  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const sentenceCount = content.split(/[.!?]+/).filter(Boolean).length;
  const correctionCount = corrections.length;

  return (
    <div className="polish-mode">
      <div className="polish-controls">
        <button
          onClick={() => isSpeaking ? stop() : speak(content)}
          aria-label={isSpeaking ? 'Stop reading' : 'Read aloud'}
          className="polish-btn"
        >
          {isSpeaking ? 'Stop' : 'Read Aloud'}
        </button>
        <button
          onClick={() => setShowStats(!showStats)}
          aria-pressed={showStats}
          className="polish-btn"
        >
          {showStats ? 'Hide Stats' : 'Show Stats'}
        </button>
      </div>

      {showStats && (
        <div className="polish-stats" role="region" aria-label="Writing statistics">
          <div className="stat">
            <span className="stat-value">{wordCount}</span>
            <span className="stat-label">Words</span>
          </div>
          <div className="stat">
            <span className="stat-value">{sentenceCount}</span>
            <span className="stat-label">Sentences</span>
          </div>
          <div className="stat">
            <span className="stat-value">{correctionCount}</span>
            <span className="stat-label">Suggestions</span>
          </div>
        </div>
      )}

      <Editor mode="polish" />
    </div>
  );
}
