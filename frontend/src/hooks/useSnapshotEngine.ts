import { useEffect, useRef, useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { snapshotManager } from '../utils/snapshotManager';
import { computeEnhancedDiff } from '../utils/diffEngine';
import { api } from '../services/api';

const REGULAR_INTERVAL = 5000; // 5 seconds
const PAUSE_THRESHOLD = 3000; // 3 seconds of inactivity
const PAUSE_CHECK_INTERVAL = 500; // Check every 500ms
const BATCH_SIZE = 5; // Batch 5 corrections before API call
const FLUSH_INTERVAL = 10000; // Flush remaining corrections every 10 seconds

interface PendingCorrection {
  originalText: string;
  correctedText: string;
  errorType: string;
  context: string;
  confidence: number;
}

export function useSnapshotEngine(editor: Editor | null) {
  const isActiveRef = useRef(false);
  const pendingCorrections = useRef<PendingCorrection[]>([]);
  const flushTimerRef = useRef<number | null>(null);

  // Batch flush function
  const flushBatch = useCallback(async () => {
    if (pendingCorrections.current.length === 0) return;

    const batch = [...pendingCorrections.current];
    pendingCorrections.current = [];

    try {
      console.log(`[Snapshot] Flushing ${batch.length} corrections`);
      await api.logCorrectionBatch(batch);
    } catch (error) {
      // Silent failure - don't interrupt writing
      console.warn('[Snapshot] Failed to log corrections:', error);
    }
  }, []);

  useEffect(() => {
    if (!editor) return;

    let regularIntervalId: NodeJS.Timeout;
    let pauseCheckIntervalId: NodeJS.Timeout;

    // Track editor activity
    const handleUpdate = () => {
      isActiveRef.current = true;
      snapshotManager.recordActivity();
    };

    editor.on('update', handleUpdate);

    // Regular snapshot interval (every 5s while typing)
    regularIntervalId = setInterval(() => {
      if (isActiveRef.current) {
        const text = editor.getText();
        snapshotManager.addSnapshot(text);
        isActiveRef.current = false;
      }
    }, REGULAR_INTERVAL);

    // Pause detection interval (every 500ms)
    pauseCheckIntervalId = setInterval(() => {
      if (snapshotManager.shouldSnapshotOnPause(PAUSE_THRESHOLD)) {
        const text = editor.getText();
        const snapshot = snapshotManager.addSnapshot(text);

        if (snapshot) {
          // Process the diff when user pauses
          processPauseDiff();
        }
      }
    }, PAUSE_CHECK_INTERVAL);

    // Periodic flush timer
    flushTimerRef.current = window.setInterval(() => {
      if (pendingCorrections.current.length > 0) {
        flushBatch();
      }
    }, FLUSH_INTERVAL);

    return () => {
      editor.off('update', handleUpdate);
      clearInterval(regularIntervalId);
      clearInterval(pauseCheckIntervalId);
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current);
      }
      // Flush on unmount
      if (pendingCorrections.current.length > 0) {
        flushBatch();
      }
    };
  }, [editor, flushBatch]);

  const processPauseDiff = useCallback(async () => {
    const pair = snapshotManager.getRecentPair();
    if (!pair) return;

    const [previous, current] = pair;

    if (!previous || !current || previous.text === current.text) {
      return;
    }

    const diffResult = computeEnhancedDiff(previous.text, current.text);

    // Filter for self-corrections only
    const selfCorrections = diffResult.changes.filter(
      change => change.signal === 'self-correction' &&
                change.oldValue &&
                change.newValue
    );

    if (selfCorrections.length === 0) return;

    console.log(`[Snapshot] Detected ${selfCorrections.length} self-corrections`);

    // Add to pending batch
    selfCorrections.forEach(change => {
      pendingCorrections.current.push({
        originalText: change.oldValue!,
        correctedText: change.newValue!,
        errorType: 'self-correction',
        context: change.context || '',
        confidence: change.similarity || 0.8,
      });
    });

    // Flush if batch is full
    if (pendingCorrections.current.length >= BATCH_SIZE) {
      await flushBatch();
    }
  }, [flushBatch]);
}
