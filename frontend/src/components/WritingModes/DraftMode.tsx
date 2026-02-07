import { useState, useEffect, useCallback, useRef } from 'react';
import { Editor } from '@tiptap/react';
import { DyslexEditor } from '../Editor/DyslexEditor';
import { EditorToolbar } from '../Editor/EditorToolbar';
import { AICoachBar } from '../Editor/AICoachBar';
import { CorrectionTooltip } from '../Editor/CorrectionTooltip';
import { ScaffoldPanel } from '../Panels/ScaffoldPanel';
import { CorrectionsPanel } from '../Panels/CorrectionsPanel';
import { VoiceBar } from '../Shared/VoiceBar';
import { StatusBar } from '../Shared/StatusBar';
import { useSnapshotEngine } from '../../hooks/useSnapshotEngine';
import { useAICoach } from '../../hooks/useAICoach';
import { useMediaRecorder } from '../../hooks/useMediaRecorder';
import { useReadAloud } from '../../hooks/useReadAloud';
import { useEditorStore, Correction } from '../../stores/editorStore';
import { useSessionStore } from '../../stores/sessionStore';
import { getCorrections } from '../../services/correctionService';
import { loadModel } from '../../services/onnxModel';
import { buildPlainToPMMap, mapRangeToPM } from '../../utils/positionMapper';

export function DraftMode() {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [tooltipCorrection, setTooltipCorrection] = useState<Correction | null>(null);
  const [tooltipRect, setTooltipRect] = useState<DOMRect | null>(null);
  const [isTooltipOpen, setIsTooltipOpen] = useState(false);

  const { content, corrections, setCorrections, clearCorrections, applyCorrection, dismissCorrection } = useEditorStore();
  const { currentNudge, dismissNudge } = useAICoach(editor);
  const { startSession, recordCorrectionApplied, recordCorrectionDismissed } = useSessionStore();
  const { isRecording, analyserNode, startRecording, stopRecording } = useMediaRecorder();
  const { speak, stop, isPlaying, isLoading } = useReadAloud();
  const correctionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastCheckedTextRef = useRef<string>('');

  useEffect(() => {
    startSession();
  }, [startSession]);

  // Preload ONNX model + dictionary on mount
  useEffect(() => {
    loadModel().catch(err => console.warn('[DraftMode] Model preload failed:', err));
  }, []);

  useSnapshotEngine(editor);

  // Debounced correction: run 800ms after user stops typing
  useEffect(() => {
    if (!editor) return;

    const plainText = editor.getText();
    if (!plainText || plainText.trim().length < 10) return;

    // Skip if text hasn't changed since last fetch
    if (plainText === lastCheckedTextRef.current) return;

    if (correctionTimerRef.current) {
      clearTimeout(correctionTimerRef.current);
    }

    correctionTimerRef.current = setTimeout(async () => {
      try {
        lastCheckedTextRef.current = plainText;
        const results = await getCorrections(plainText);
        // Map plain-text offsets → ProseMirror positions
        const posMap = buildPlainToPMMap(editor);
        const mapped: Correction[] = [];
        results.forEach((c, i) => {
          const pmRange = mapRangeToPM(posMap, c.start, c.end);
          if (!pmRange) return;
          mapped.push({
            id: `qc-${pmRange.start}-${pmRange.end}-${i}`,
            original: c.original,
            suggested: c.suggested,
            type: c.type,
            start: pmRange.start,
            end: pmRange.end,
            explanation: c.explanation,
          });
        });
        setCorrections(mapped);
      } catch (err) {
        console.warn('[DraftMode] Correction failed:', err);
      }
    }, 800);

    return () => {
      if (correctionTimerRef.current) {
        clearTimeout(correctionTimerRef.current);
      }
    };
  }, [content, editor, setCorrections]);

  useEffect(() => {
    const handleCorrectionClick = (e: CustomEvent) => {
      const { correctionId, rect } = e.detail;
      const correction = corrections.find((c) => c.id === correctionId);
      if (correction) {
        setTooltipCorrection(correction);
        setTooltipRect(rect);
        setIsTooltipOpen(true);
      }
    };

    document.addEventListener('correction-click', handleCorrectionClick as EventListener);
    return () => {
      document.removeEventListener('correction-click', handleCorrectionClick as EventListener);
    };
  }, [corrections]);

  const handleCorrectionClick = useCallback((correction: Correction, rect: DOMRect) => {
    setTooltipCorrection(correction);
    setTooltipRect(rect);
    setIsTooltipOpen(true);
  }, []);

  // Clear corrections on unmount
  useEffect(() => {
    return () => {
      clearCorrections();
    };
  }, [clearCorrections]);

  const handleApplyCorrection = () => {
    if (!tooltipCorrection || !editor) return;
    editor
      .chain()
      .focus()
      .insertContentAt(
        { from: tooltipCorrection.start, to: tooltipCorrection.end },
        tooltipCorrection.suggested
      )
      .run();
    applyCorrection(tooltipCorrection.id);
    recordCorrectionApplied();
    // Clear stale corrections — the debounced re-fetch will get fresh ones
    clearCorrections();
    lastCheckedTextRef.current = '';
    setIsTooltipOpen(false);
    setTooltipCorrection(null);
  };

  const handleDismissCorrection = () => {
    if (!tooltipCorrection) return;
    dismissCorrection(tooltipCorrection.id);
    recordCorrectionDismissed();
    setIsTooltipOpen(false);
    setTooltipCorrection(null);
  };

  const handleReadAloud = async () => {
    if (isPlaying || isLoading) {
      stop();
    } else {
      await speak(content);
    }
  };

  return (
    <div className="draft-mode-layout">
      <ScaffoldPanel editor={editor} />

      <div className="draft-mode-center">
        <div className="draft-mode-scroll">
          <div className="draft-toolbar-row">
            <EditorToolbar editor={editor} />
            <button
              onClick={handleReadAloud}
              aria-label={isLoading ? 'Loading audio' : isPlaying ? 'Stop reading' : 'Read aloud'}
              className="btn btn-secondary"
              disabled={isLoading || !content.trim()}
            >
              {isLoading ? 'Loading...' : isPlaying ? 'Stop' : 'Read Aloud'}
            </button>
          </div>

          <div className="draft-page">
            <DyslexEditor
              onEditorReady={setEditor}
              onCorrectionClick={handleCorrectionClick}
            />
          </div>

          <AICoachBar nudge={currentNudge} onDismiss={dismissNudge} />
        </div>

        <VoiceBar
          isRecording={isRecording}
          isTranscribing={false}
          analyserNode={analyserNode}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          compact
        />

        <StatusBar />
      </div>

      <CorrectionsPanel editor={editor} />

      <CorrectionTooltip
        correction={tooltipCorrection}
        anchorRect={tooltipRect}
        isOpen={isTooltipOpen}
        onClose={() => setIsTooltipOpen(false)}
        onApply={handleApplyCorrection}
        onDismiss={handleDismissCorrection}
      />
    </div>
  );
}
