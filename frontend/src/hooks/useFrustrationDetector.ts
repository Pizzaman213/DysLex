/**
 * Frustration Detection Hook
 *
 * Passively monitors writing behavior for signs of frustration:
 * 1. Rapid Deletion (>20 chars in 3 seconds)
 * 2. Long Pause (>30 seconds mid-sentence)
 * 3. Short Bursts (<5 words, 3+ times in a row)
 * 4. Cursor Thrashing (5+ jumps >50 chars in 10 seconds)
 *
 * When frustration threshold is exceeded, triggers empathetic check-in.
 * Enforces 10-minute cooldown to avoid annoyance.
 */

import { useEffect, useRef, useState } from 'react';
import type { Editor } from '@tiptap/react';
import { useSessionStore } from '../stores/sessionStore';

interface FrustrationSignal {
  type: 'rapid_deletion' | 'long_pause' | 'short_burst' | 'cursor_thrash';
  timestamp: number;
  severity: number; // 0-1 scale
  metadata?: Record<string, any>;
}

interface DeletionEvent {
  charCount: number;
  timestamp: number;
}

interface TypingBurst {
  wordsAdded: number;
  startTime: number;
  endTime: number;
}

interface CursorPosition {
  from: number;
  to: number;
  timestamp: number;
}

// Configuration constants
const SIGNAL_WEIGHTS = {
  rapid_deletion: 0.4,
  long_pause: 0.2,
  short_burst: 0.3,
  cursor_thrash: 0.3,
};

const SIGNAL_DECAY_MS = 120000; // 2 minutes - signals decay over time
const FRUSTRATION_THRESHOLD = 0.6;
const CHECK_IN_COOLDOWN = 600000; // 10 minutes
const INTERVENTION_SPACING = 120000; // 2 minutes between any intervention

// Detection thresholds
const RAPID_DELETION_THRESHOLD = 20; // chars
const RAPID_DELETION_WINDOW = 3000; // ms
const LONG_PAUSE_THRESHOLD = 30000; // ms
const SHORT_BURST_THRESHOLD = 5; // words
const SHORT_BURST_COUNT = 3; // consecutive bursts
const CURSOR_JUMP_DISTANCE = 50; // chars
const CURSOR_JUMP_COUNT = 5; // jumps
const CURSOR_JUMP_WINDOW = 10000; // ms

/**
 * Calculate weighted frustration score with exponential decay.
 */
function calculateFrustrationScore(signals: FrustrationSignal[]): number {
  const now = Date.now();

  return signals.reduce((score, signal) => {
    // Exponential decay over 2 minutes
    const age = now - signal.timestamp;
    const decayFactor = Math.exp(-age / SIGNAL_DECAY_MS);

    const weight = SIGNAL_WEIGHTS[signal.type];
    return score + (weight * signal.severity * decayFactor);
  }, 0);
}

export function useFrustrationDetector(editor: Editor | null) {
  const [shouldShowCheckIn, setShouldShowCheckIn] = useState(false);
  const [checkInSignals, setCheckInSignals] = useState<string[]>([]);

  // Refs for tracking state without re-renders
  const lastCheckInTimeRef = useRef(0);
  const frustrationSignalsRef = useRef<FrustrationSignal[]>([]);
  const lastActivityTimeRef = useRef(Date.now());

  // Signal-specific tracking
  const deletionWindowRef = useRef<DeletionEvent[]>([]);
  const burstHistoryRef = useRef<TypingBurst[]>([]);
  const currentBurstRef = useRef<{ words: number; startTime: number } | null>(null);
  const cursorHistoryRef = useRef<CursorPosition[]>([]);
  const lastWordCountRef = useRef(0);

  /**
   * Record a frustration signal and check if threshold is exceeded.
   */
  const recordFrustrationSignal = (signal: Omit<FrustrationSignal, 'timestamp'>) => {
    const fullSignal: FrustrationSignal = { ...signal, timestamp: Date.now() };
    frustrationSignalsRef.current.push(fullSignal);

    // Record in sessionStore
    useSessionStore.getState().recordFrustrationSignal(fullSignal);

    // Check if threshold exceeded
    const score = calculateFrustrationScore(frustrationSignalsRef.current);

    if (score >= FRUSTRATION_THRESHOLD) {
      const now = Date.now();

      // Enforce 10-minute cooldown
      if (now - lastCheckInTimeRef.current >= CHECK_IN_COOLDOWN) {
        // Check for recent AI Coach activity
        const lastCoachNudgeTime = useSessionStore.getState().lastInterventionTime;
        if (lastCoachNudgeTime && now - lastCoachNudgeTime < INTERVENTION_SPACING) {
          return; // Suppress check-in to avoid intervention overlap
        }

        // Get active signal types (from last minute)
        const activeSignals = frustrationSignalsRef.current
          .filter(s => now - s.timestamp < 60000)
          .map(s => s.type);

        // Remove duplicates
        const uniqueSignals = Array.from(new Set(activeSignals));

        setShouldShowCheckIn(true);
        setCheckInSignals(uniqueSignals);
        lastCheckInTimeRef.current = now;

        // Record in sessionStore
        useSessionStore.getState().recordCheckInShown(uniqueSignals);
      }
    }
  };

  /**
   * Dismiss the check-in prompt and clear signals.
   */
  const dismissCheckIn = () => {
    setShouldShowCheckIn(false);
    setCheckInSignals([]);
    frustrationSignalsRef.current = []; // Clear signals

    // Record dismissal in sessionStore
    useSessionStore.getState().recordCheckInDismissal();
  };

  /**
   * Handle user action from check-in prompt.
   */
  const handleCheckInAction = (action: string) => {
    setShouldShowCheckIn(false);
    setCheckInSignals([]);
    frustrationSignalsRef.current = [];

    // Record action in sessionStore
    useSessionStore.getState().recordCheckInAction(action);

    // Trigger action
    if (action === 'voice_mode') {
      // TODO: Navigate to capture mode or activate voice input
      // This will be implemented when integrating with mode switching
      console.log('Switching to voice mode...');
    } else if (action === 'take_break') {
      // TODO: Could show a timer or meditation prompt
      console.log('Taking a break...');
    }
  };

  // Setup detection when editor is ready
  useEffect(() => {
    if (!editor) return;

    // 1. Rapid Deletion Detection
    const handleTransaction = ({ transaction }: any) => {
      if (!transaction.docChanged) return;

      // Calculate net character change
      const before = transaction.before.content.size;
      const after = transaction.doc.content.size;
      const netChange = after - before;

      // If deletion (negative change)
      if (netChange < 0) {
        const charCount = Math.abs(netChange);
        const now = Date.now();

        // Add to rolling window
        deletionWindowRef.current.push({ charCount, timestamp: now });

        // Remove events older than window
        deletionWindowRef.current = deletionWindowRef.current.filter(
          e => now - e.timestamp < RAPID_DELETION_WINDOW
        );

        // Sum deletions in window
        const totalDeleted = deletionWindowRef.current.reduce(
          (sum, e) => sum + e.charCount,
          0
        );

        // Trigger signal if threshold exceeded
        if (totalDeleted >= RAPID_DELETION_THRESHOLD) {
          recordFrustrationSignal({
            type: 'rapid_deletion',
            severity: Math.min(1.0, totalDeleted / 40),
            metadata: { totalDeleted, windowSize: deletionWindowRef.current.length }
          });

          // Clear window to avoid duplicate triggers
          deletionWindowRef.current = [];
        }
      }
    };

    editor.on('transaction', handleTransaction);

    // 2. Update activity time on any editor change
    const handleUpdate = () => {
      lastActivityTimeRef.current = Date.now();

      // Track word count for burst detection
      const currentWordCount = editor.storage.characterCount?.words() || 0;

      if (!currentBurstRef.current) {
        currentBurstRef.current = {
          words: currentWordCount,
          startTime: Date.now()
        };
      } else {
        currentBurstRef.current.words = currentWordCount;
      }
    };

    editor.on('update', handleUpdate);

    // 3. Cursor Thrashing Detection
    const handleSelectionUpdate = () => {
      const { from, to } = editor.state.selection;
      const now = Date.now();

      // Add to history
      cursorHistoryRef.current.push({ from, to, timestamp: now });

      // Remove events older than window
      cursorHistoryRef.current = cursorHistoryRef.current.filter(
        e => now - e.timestamp < CURSOR_JUMP_WINDOW
      );

      // Count significant jumps (>50 chars)
      let jumpCount = 0;
      for (let i = 1; i < cursorHistoryRef.current.length; i++) {
        const prev = cursorHistoryRef.current[i - 1];
        const curr = cursorHistoryRef.current[i];
        const distance = Math.abs(curr.from - prev.from);

        if (distance > CURSOR_JUMP_DISTANCE) {
          jumpCount++;
        }
      }

      // Trigger if threshold exceeded
      if (jumpCount >= CURSOR_JUMP_COUNT) {
        recordFrustrationSignal({
          type: 'cursor_thrash',
          severity: Math.min(1.0, jumpCount / 10),
          metadata: { jumpCount }
        });

        // Clear history to avoid duplicate triggers
        cursorHistoryRef.current = [];
      }
    };

    editor.on('selectionUpdate', handleSelectionUpdate);

    // Cleanup
    return () => {
      editor.off('transaction', handleTransaction);
      editor.off('update', handleUpdate);
      editor.off('selectionUpdate', handleSelectionUpdate);
    };
  }, [editor]);

  // 4. Long Pause Detection (check every 5 seconds)
  useEffect(() => {
    if (!editor) return;

    const intervalId = setInterval(() => {
      const idleTime = Date.now() - lastActivityTimeRef.current;

      if (idleTime >= LONG_PAUSE_THRESHOLD) {
        // Only trigger if cursor is mid-sentence
        const { from } = editor.state.selection;
        const $pos = editor.state.doc.resolve(from);
        const paragraph = $pos.parent;
        const cursorPos = from - $pos.start();

        // Check if not at start or end of paragraph
        const isMidSentence = cursorPos > 0 && cursorPos < paragraph.content.size;

        if (isMidSentence) {
          recordFrustrationSignal({
            type: 'long_pause',
            severity: Math.min(1.0, (idleTime - LONG_PAUSE_THRESHOLD) / 30000),
            metadata: { idleTime }
          });

          // Reset activity time to avoid repeated triggers
          lastActivityTimeRef.current = Date.now();
        }
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [editor]);

  // 5. Short Burst Detection (check every 2 seconds)
  useEffect(() => {
    if (!editor) return;

    const intervalId = setInterval(() => {
      const idleTime = Date.now() - lastActivityTimeRef.current;

      // Pause detected (>2 seconds idle)
      if (idleTime >= 2000 && currentBurstRef.current) {
        const currentWordCount = editor.storage.characterCount?.words() || 0;
        const wordsAdded = currentWordCount - lastWordCountRef.current;

        const burst: TypingBurst = {
          wordsAdded,
          startTime: currentBurstRef.current.startTime,
          endTime: Date.now()
        };

        burstHistoryRef.current.push(burst);
        currentBurstRef.current = null;
        lastWordCountRef.current = currentWordCount;

        // Keep only last 10 bursts
        if (burstHistoryRef.current.length > 10) {
          burstHistoryRef.current = burstHistoryRef.current.slice(-10);
        }

        // Check for short burst pattern (last 3 bursts all <5 words)
        const recentBursts = burstHistoryRef.current.slice(-SHORT_BURST_COUNT);
        if (recentBursts.length === SHORT_BURST_COUNT) {
          const allShort = recentBursts.every(b => b.wordsAdded < SHORT_BURST_THRESHOLD && b.wordsAdded > 0);

          if (allShort) {
            recordFrustrationSignal({
              type: 'short_burst',
              severity: 0.8,
              metadata: {
                burstCount: recentBursts.length,
                avgWords: recentBursts.reduce((sum, b) => sum + b.wordsAdded, 0) / recentBursts.length
              }
            });

            // Clear history to avoid duplicate triggers
            burstHistoryRef.current = [];
          }
        }
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [editor]);

  return {
    shouldShowCheckIn,
    checkInSignals,
    dismissCheckIn,
    handleCheckInAction,
  };
}
