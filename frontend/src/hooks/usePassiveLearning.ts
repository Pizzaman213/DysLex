import { useState, useCallback, useRef } from 'react';
import { computeWordDiff, type DiffResult } from '../utils/diffEngine';
import { useEditorStore } from '../stores/editorStore';

interface Snapshot {
  text: string;
  timestamp: number;
}

export function usePassiveLearning() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [diffs, setDiffs] = useState<DiffResult[]>([]);
  const lastSnapshotRef = useRef<string>('');
  const { setCorrections } = useEditorStore();

  const takeSnapshot = useCallback((text: string) => {
    if (text === lastSnapshotRef.current) {
      return;
    }

    lastSnapshotRef.current = text;
    const snapshot: Snapshot = {
      text,
      timestamp: Date.now(),
    };

    setSnapshots((prev) => [...prev.slice(-10), snapshot]);
  }, []);

  const computeDiff = useCallback(() => {
    if (snapshots.length < 2) {
      return;
    }

    const previousSnapshot = snapshots[snapshots.length - 2];
    const currentSnapshot = snapshots[snapshots.length - 1];

    const diff = computeWordDiff(previousSnapshot.text, currentSnapshot.text);

    if (diff.changes.length > 0) {
      setDiffs((prev) => [...prev.slice(-50), diff]);

      // Analyze user corrections for passive learning
      analyzeUserCorrections(diff);
    }
  }, [snapshots]);

  const analyzeUserCorrections = useCallback((diff: DiffResult) => {
    // Look for patterns where user replaced incorrect words with correct ones
    // This data feeds into the error profile
    const userCorrections = diff.changes.filter(
      (change) => change.type === 'replace'
    );

    if (userCorrections.length > 0) {
      // Send to backend for error profile update
      // api.reportUserCorrections(userCorrections);
    }
  }, []);

  const clearHistory = useCallback(() => {
    setSnapshots([]);
    setDiffs([]);
    lastSnapshotRef.current = '';
  }, []);

  return {
    takeSnapshot,
    computeDiff,
    clearHistory,
    snapshotCount: snapshots.length,
    diffCount: diffs.length,
  };
}
