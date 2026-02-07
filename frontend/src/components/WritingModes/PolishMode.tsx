import { useState, useEffect } from 'react';
import { Editor } from '@tiptap/react';
import { DyslexEditor } from '../Editor/DyslexEditor';
import { EditorToolbar } from '../Editor/EditorToolbar';
import { PolishPanel } from '../Panels/PolishPanel';
import { StatusBar } from '../Shared/StatusBar';
import { useReadAloud } from '../../hooks/useReadAloud';
import { useEditorStore } from '../../stores/editorStore';
import { usePolishStore } from '../../stores/polishStore';

export function PolishMode() {
  const { content } = useEditorStore();
  const { setActiveSuggestion } = usePolishStore();
  const { speak, stop, isPlaying, isLoading } = useReadAloud();
  const [editor, setEditor] = useState<Editor | null>(null);

  useEffect(() => {
    const handleTrackedChangeClick = (e: Event) => {
      const customEvent = e as CustomEvent;
      const { suggestionId } = customEvent.detail;
      if (suggestionId) {
        setActiveSuggestion(suggestionId);
      }
    };

    document.addEventListener('tracked-change-click', handleTrackedChangeClick);
    return () => {
      document.removeEventListener('tracked-change-click', handleTrackedChangeClick);
    };
  }, [setActiveSuggestion]);

  const handleEditorReady = (editorInstance: Editor) => {
    setEditor(editorInstance);
  };

  const handleReadAloud = async () => {
    if (isPlaying || isLoading) {
      stop();
    } else {
      await speak(content);
    }
  };

  return (
    <div className="polish-mode">
      <div className="polish-layout">
        <div className="polish-editor-area">
          <div className="polish-controls">
            <button
              onClick={handleReadAloud}
              aria-label={isLoading ? 'Loading audio' : isPlaying ? 'Stop reading' : 'Read aloud'}
              className="btn btn-secondary"
              disabled={isLoading}
            >
              {isLoading ? 'Loading...' : isPlaying ? 'Stop' : 'Read Aloud'}
            </button>
            {editor && <EditorToolbar editor={editor} />}
          </div>

          <DyslexEditor
            mode="polish"
            onEditorReady={handleEditorReady}
          />

          <StatusBar />
        </div>

        <PolishPanel editor={editor} />
      </div>
    </div>
  );
}
