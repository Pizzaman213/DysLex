import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { DyslexEditor } from '../Editor/DyslexEditor';
import { EditorToolbar } from '../Editor/EditorToolbar';
import { CoachPanel } from '../Panels/CoachPanel';
import { PolishPanel } from '../Panels/PolishPanel';
import { VoiceBar } from '../Shared/VoiceBar';
import { StatusBar } from '../Shared/StatusBar';
import { useCaptureVoice } from '../../hooks/useCaptureVoice';
import { useReadAloud } from '../../hooks/useReadAloud';
import { useEditorStore } from '../../stores/editorStore';
import { usePolishStore } from '../../stores/polishStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useFormatStore } from '../../stores/formatStore';
import { PAPER_FORMATS } from '../../constants/paperFormats';
import { PAGE_DIMENSIONS, PAGE_MARGIN, getContentHeight } from '../../constants/pageDimensions';
export function PolishMode() {
  const { content } = useEditorStore();
  const { setActiveSuggestion } = usePolishStore();
  const pageType = useSettingsStore((s) => s.pageType);
  const viewMode = useSettingsStore((s) => s.viewMode);
  const zoom = useSettingsStore((s) => s.zoom);
  const pageNumbers = useSettingsStore((s) => s.pageNumbers);
  const togglePageNumbers = useSettingsStore((s) => s.togglePageNumbers);
  const activeFormat = useFormatStore((s) => s.activeFormat);
  const authorLastName = useFormatStore((s) => s.authorLastName);
  const shortenedTitle = useFormatStore((s) => s.shortenedTitle);
  const runningHeaderType = activeFormat !== 'none' ? PAPER_FORMATS[activeFormat]?.runningHeaderType || '' : '';

  const pageStyle = useMemo(() => {
    const dim = PAGE_DIMENSIONS[pageType];
    return {
      '--page-width': `${dim.width}px`,
      '--page-height': `${dim.height}px`,
      '--page-margin': `${PAGE_MARGIN}px`,
      '--page-content-height': `${getContentHeight(pageType)}px`,
    } as React.CSSProperties;
  }, [pageType]);
  const { isRecording, transcript: voiceTranscript, interimText, analyserNode, isTranscribing, micDenied, start: startVoice, stop: stopVoice } = useCaptureVoice();
  const { speak, stop, isPlaying, isLoading } = useReadAloud();
  const [editor, setEditor] = useState<Editor | null>(null);
  const lastInsertedVoiceRef = useRef<string>('');

  // Batch-insert finalized voice text into editor as it arrives
  useEffect(() => {
    if (!isRecording || !editor || interimText) return;

    const lastInserted = lastInsertedVoiceRef.current;
    if (voiceTranscript.length > lastInserted.length) {
      const delta = voiceTranscript.slice(lastInserted.length);
      if (delta.trim()) {
        editor.chain().focus().insertContent(delta).run();
        lastInsertedVoiceRef.current = voiceTranscript;
      }
    }
  }, [isRecording, voiceTranscript, interimText, editor]);

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
      // read-aloud should get raw text, not markup — updated 2/7 connor
      const plainText = editor?.getText() ?? '';
      await speak(plainText);
    }
  };

  const [showAnalysis, setShowAnalysis] = useState(true);

  const handlePageDoubleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (viewMode === 'continuous') return;

    const target = e.currentTarget;
    const rect = target.getBoundingClientRect();
    const scale = zoom / 100;
    const margin = PAGE_MARGIN * scale;

    const relativeY = e.clientY - rect.top;
    const relativeBottom = rect.bottom - e.clientY;

    if (relativeY < margin || relativeBottom < margin) {
      e.preventDefault();
      togglePageNumbers();
    }
  }, [viewMode, zoom, togglePageNumbers]);

  return (
    <div className="polish-mode">
      <div className={`polish-layout${showAnalysis ? '' : ' panel-hidden'}`}>
        <div className="polish-coach-panel">
          <CoachPanel editor={editor} />
        </div>

        <div className="polish-editor-area">
          <div className="draft-toolbar-row">
            <EditorToolbar
              editor={editor}
              panelsVisible={showAnalysis}
              onTogglePanels={() => setShowAnalysis(prev => !prev)}
              onReadAloud={handleReadAloud}
              isReadAloudPlaying={isPlaying}
              isReadAloudLoading={isLoading}
              readAloudDisabled={!content.trim()}
            />
          </div>

          <div className={`polish-scroll view-${viewMode}`} style={{ '--editor-zoom': zoom / 100 } as React.CSSProperties}>
            <div
              className="editor-page"
              style={pageStyle}
              data-page-numbers={pageNumbers}
              data-running-header-type={runningHeaderType}
              data-header-last-name={authorLastName}
              data-header-title={shortenedTitle}
              onDoubleClick={handlePageDoubleClick}
            >
              <DyslexEditor
                mode="polish"
                onEditorReady={handleEditorReady}
              />
            </div>
          </div>

          <VoiceBar
            isRecording={isRecording}
            isTranscribing={isTranscribing}
            analyserNode={analyserNode}
            onStartRecording={() => {
              lastInsertedVoiceRef.current = '';
              startVoice();
            }}
            onStopRecording={async () => {
              const text = await stopVoice();
              if (text && editor) {
                const remaining = text.slice(lastInsertedVoiceRef.current.length);
                if (remaining.trim()) {
                  editor.chain().focus().insertContent(remaining).run();
                }
              }
              lastInsertedVoiceRef.current = '';
            }}
            compact
            onReadAloud={handleReadAloud}
            isReadAloudPlaying={isPlaying}
            isReadAloudLoading={isLoading}
            readAloudDisabled={!content.trim()}
            micDenied={micDenied}
          />

          <StatusBar />
        </div>

        <PolishPanel editor={editor} />
      </div>
    </div>
  );
}
