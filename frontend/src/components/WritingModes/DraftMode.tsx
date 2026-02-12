import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Editor } from '@tiptap/react';
import { DyslexEditor } from '../Editor/DyslexEditor';
import { EditorToolbar } from '../Editor/EditorToolbar';
import { AICoachBar } from '../Editor/AICoachBar';
import { CorrectionTooltip } from '../Editor/CorrectionTooltip';
import { ContextMenu } from '../Layout/ContextMenu';
import type { ContextMenuItem } from '../Layout/ContextMenu';
import { ScaffoldPanel } from '../Panels/ScaffoldPanel';
import { RightPanel } from '../Panels/RightPanel';
import { VoiceBar } from '../Shared/VoiceBar';
import { StatusBar } from '../Shared/StatusBar';
import { useSnapshotEngine } from '../../hooks/useSnapshotEngine';
import { useTtsPrewarmer } from '../../hooks/useTtsPrewarmer';
import { useAICoach } from '../../hooks/useAICoach';
import { useCaptureVoice } from '../../hooks/useCaptureVoice';
import { useReadAloud } from '../../hooks/useReadAloud';
import { useEditorStore, Correction } from '../../stores/editorStore';
import { useSessionStore } from '../../stores/sessionStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useFormatStore } from '../../stores/formatStore';
import { PAPER_FORMATS } from '../../constants/paperFormats';
import { getCorrections } from '../../services/correctionService';
import { loadModel, addToLocalDictionary } from '../../services/onnxModel';
import { api } from '../../services/api';
import { buildPlainToPMMap, mapRangeToPM } from '../../utils/positionMapper';
import { PAGE_DIMENSIONS, PAGE_MARGIN, getContentHeight } from '../../constants/pageDimensions';
export function DraftMode() {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [tooltipCorrection, setTooltipCorrection] = useState<Correction | null>(null);
  const [tooltipRect, setTooltipRect] = useState<DOMRect | null>(null);
  const [isTooltipOpen, setIsTooltipOpen] = useState(false);
  const [panelsVisible, setPanelsVisible] = useState(true);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; word: string } | null>(null);
  const { content, corrections, setCorrections, clearCorrections, applyCorrection, dismissCorrection } = useEditorStore();
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
  const { currentNudge, dismissNudge } = useAICoach(editor);
  const { startSession, recordCorrectionApplied, recordCorrectionDismissed } = useSessionStore();
  const { isRecording, transcript: voiceTranscript, interimText, analyserNode, isTranscribing, micDenied, start: startVoice, stop: stopVoice } = useCaptureVoice();
  const { speak, stop, isPlaying, isLoading } = useReadAloud();
  const correctionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastCheckedTextRef = useRef<string>('');
  const lastInsertedVoiceRef = useRef<string>('');

  useEffect(() => {
    startSession();
  }, [startSession]);

  // Preload ONNX model + dictionary on mount
  useEffect(() => {
    loadModel().catch(err => console.warn('[DraftMode] Model preload failed:', err));
  }, []);

  useSnapshotEngine(editor);
  useTtsPrewarmer(editor);

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

  // Switched from content-dep to editor.on('update') so corrections fire reliably — C. Secrist 2/8
  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => {
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
          const idCounts = new Map<string, number>();
          results.forEach((c) => {
            const pmRange = mapRangeToPM(posMap, c.start, c.end);
            if (!pmRange) return;
            // Use content-based IDs so applied/dismissed state survives re-fetch (feb 9 fix)
            const baseKey = `${c.original}::${c.suggested}`;
            const count = idCounts.get(baseKey) || 0;
            idCounts.set(baseKey, count + 1);
            mapped.push({
              id: `qc-${c.original}-${c.suggested}-${count}`,
              original: c.original,
              suggested: c.suggested,
              type: c.type,
              start: pmRange.start,
              end: pmRange.end,
              explanation: c.explanation,
            });
          });
          if (results.length > 0 && mapped.length === 0) {
            console.warn('[DraftMode] All %d corrections lost during position mapping', results.length);
          }
          setCorrections(mapped);
        } catch (err) {
          console.warn('[DraftMode] Correction failed:', err);
        }
      }, 800);
    };

    editor.on('update', handleUpdate);

    // Run once immediately for existing content
    handleUpdate();

    return () => {
      editor.off('update', handleUpdate);
      if (correctionTimerRef.current) {
        clearTimeout(correctionTimerRef.current);
      }
    };
  }, [editor, setCorrections]);

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

    // Search for the original text in the document and replace it.
    // This is more robust than using mapped positions which can drift.
    const { doc } = editor.state;
    let applied = false;
    doc.descendants((node, pos) => {
      if (applied) return false;
      if (node.isText && node.text) {
        const idx = node.text.indexOf(tooltipCorrection.original);
        if (idx !== -1) {
          const from = pos + idx;
          const to = from + tooltipCorrection.original.length;
          editor.chain().focus()
            .insertContentAt({ from, to }, tooltipCorrection.suggested)
            .run();
          applied = true;
          return false;
        }
      }
      return true;
    });

    applyCorrection(tooltipCorrection.id);
    recordCorrectionApplied();
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
      // feed plain text to TTS, not HTML — connor s. feb 7
      const plainText = editor?.getText() ?? '';
      await speak(plainText);
    }
  };

  // Right-click context menu — "Add to Dictionary"
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    if (!editor) return;

    // Get the word under the cursor from the browser selection
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount) return;

    const range = selection.getRangeAt(0);
    const node = range.startContainer;
    if (node.nodeType !== Node.TEXT_NODE || !node.textContent) return;

    const text = node.textContent;
    const offset = range.startOffset;

    // Find word boundaries around the cursor
    let start = offset;
    let end = offset;
    while (start > 0 && /\w/.test(text[start - 1])) start--;
    while (end < text.length && /\w/.test(text[end])) end++;

    const word = text.slice(start, end).trim();
    if (!word || word.length < 2) return;

    // Only show custom menu if the word has an active correction
    const hasCorrection = corrections.some(
      (c) => c.original.toLowerCase() === word.toLowerCase()
    );
    if (!hasCorrection) return;

    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, word });
  }, [editor, corrections]);

  const handleAddToDictionary = useCallback((word: string) => {
    // Add to local dictionary (immediate, no API needed)
    addToLocalDictionary(word);

    // Dismiss all corrections for this word
    corrections
      .filter((c) => c.original.toLowerCase() === word.toLowerCase())
      .forEach((c) => dismissCorrection(c.id));

    // Re-trigger corrections to clear stale ones
    lastCheckedTextRef.current = '';

    // Also persist to backend (fire-and-forget)
    const userId = '00000000-0000-0000-0000-000000000000';
    api.addToDictionary(userId, word).catch(() => {
      // Backend is optional — local dictionary is the source of truth
    });

    setContextMenu(null);
  }, [corrections, dismissCorrection]);

  const contextMenuItems: ContextMenuItem[] = contextMenu ? [
    {
      label: `Add "${contextMenu.word}" to Dictionary`,
      onClick: () => handleAddToDictionary(contextMenu.word),
    },
  ] : [];

  const handlePageDoubleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (viewMode === 'continuous') return;

    const target = e.currentTarget;
    const rect = target.getBoundingClientRect();
    const scale = zoom / 100;
    const margin = PAGE_MARGIN * scale;

    // Click position relative to the page container
    const relativeY = e.clientY - rect.top;
    const relativeBottom = rect.bottom - e.clientY;

    // Check if click is in top or bottom margin
    if (relativeY < margin || relativeBottom < margin) {
      e.preventDefault();
      togglePageNumbers();
    }
  }, [viewMode, zoom, togglePageNumbers]);

  return (
    <div className={`draft-mode-layout${panelsVisible ? '' : ' panels-hidden'}`}>
      <ScaffoldPanel editor={editor} />

      <div className="draft-mode-center">
        <div className={`draft-mode-scroll view-${viewMode}`} style={{ '--editor-zoom': zoom / 100 } as React.CSSProperties}>
          <div className="draft-toolbar-row">
            <EditorToolbar
              editor={editor}
              panelsVisible={panelsVisible}
              onTogglePanels={() => setPanelsVisible((v) => !v)}
              onReadAloud={handleReadAloud}
              isReadAloudPlaying={isPlaying}
              isReadAloudLoading={isLoading}
              readAloudDisabled={!content.trim()}
            />
          </div>

          <div
            className="draft-page"
            style={pageStyle}
            data-page-numbers={pageNumbers}
            data-running-header-type={runningHeaderType}
            data-header-last-name={authorLastName}
            data-header-title={shortenedTitle}
            onDoubleClick={handlePageDoubleClick}
            onContextMenu={handleContextMenu}
          >
            <DyslexEditor
              onEditorReady={setEditor}
              onCorrectionClick={handleCorrectionClick}
            />
          </div>

          <AICoachBar nudge={currentNudge} onDismiss={dismissNudge} />
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

      <RightPanel editor={editor} />

      <CorrectionTooltip
        correction={tooltipCorrection}
        anchorRect={tooltipRect}
        isOpen={isTooltipOpen}
        onClose={() => setIsTooltipOpen(false)}
        onApply={handleApplyCorrection}
        onDismiss={handleDismissCorrection}
      />

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenuItems}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
}
