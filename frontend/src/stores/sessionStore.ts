/**
 * Session Store
 *
 * Tracks writing session statistics with localStorage persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FrustrationEvent {
  type: 'rapid_deletion' | 'long_pause' | 'short_burst' | 'cursor_thrash';
  timestamp: number;
  severity: number;
  metadata?: Record<string, any>;
}

interface CheckInEvent {
  timestamp: number;
  signalTypes: string[];
  action: 'dismissed' | 'took_break' | 'voice_mode' | 'continued' | null;
}

interface SessionState {
  startTime: number | null;
  totalWordsWritten: number;
  correctionsApplied: number;
  correctionsDismissed: number;
  lastInterventionTime: number | null;

  // Frustration tracking
  frustrationEvents: FrustrationEvent[];
  checkInHistory: CheckInEvent[];
  lastCheckInTime: number | null;

  startSession: () => void;
  endSession: () => void;
  incrementWords: (count: number) => void;
  recordCorrectionApplied: () => void;
  recordCorrectionDismissed: () => void;
  getTimeSpent: () => number;

  // Frustration tracking methods
  recordFrustrationSignal: (signal: FrustrationEvent) => void;
  recordCheckInShown: (signalTypes: string[]) => void;
  recordCheckInAction: (action: string) => void;
  recordCheckInDismissal: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      startTime: null,
      totalWordsWritten: 0,
      correctionsApplied: 0,
      correctionsDismissed: 0,
      lastInterventionTime: null,
      frustrationEvents: [],
      checkInHistory: [],
      lastCheckInTime: null,

      startSession: () => {
        const now = Date.now();
        set({
          startTime: now,
          totalWordsWritten: 0,
          correctionsApplied: 0,
          correctionsDismissed: 0,
          lastInterventionTime: null,
          frustrationEvents: [],
          checkInHistory: [],
          lastCheckInTime: null
        });
      },

      endSession: () => {
        set({
          startTime: null,
          totalWordsWritten: 0,
          correctionsApplied: 0,
          correctionsDismissed: 0,
          lastInterventionTime: null,
          frustrationEvents: [],
          checkInHistory: [],
          lastCheckInTime: null
        });
      },

      incrementWords: (count) =>
        set((state) => ({
          totalWordsWritten: state.totalWordsWritten + count
        })),

      recordCorrectionApplied: () =>
        set((state) => ({
          correctionsApplied: state.correctionsApplied + 1
        })),

      recordCorrectionDismissed: () =>
        set((state) => ({
          correctionsDismissed: state.correctionsDismissed + 1
        })),

      getTimeSpent: () => {
        const { startTime } = get();
        if (!startTime) return 0;
        const elapsed = Date.now() - startTime;
        return Math.floor(elapsed / 60000); // Convert to minutes
      },

      recordFrustrationSignal: (signal) => {
        set((state) => ({
          frustrationEvents: [...state.frustrationEvents, signal]
        }));
      },

      recordCheckInShown: (signalTypes) => {
        set({
          lastCheckInTime: Date.now(),
          lastInterventionTime: Date.now(),
          checkInHistory: [
            ...get().checkInHistory,
            {
              timestamp: Date.now(),
              signalTypes,
              action: null
            }
          ]
        });
      },

      recordCheckInAction: (action) => {
        set((state) => {
          const lastCheckIn = state.checkInHistory[state.checkInHistory.length - 1];
          if (lastCheckIn) {
            lastCheckIn.action = action as any;
          }
          return { checkInHistory: [...state.checkInHistory] };
        });
      },

      recordCheckInDismissal: () => {
        get().recordCheckInAction('dismissed');
      }
    }),
    {
      name: 'dyslex-session'
    }
  )
);
