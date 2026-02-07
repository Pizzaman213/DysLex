/**
 * Zustand store for Capture Mode state management.
 */

import { create } from 'zustand';

export type CapturePhase = 'idle' | 'recording' | 'transcribing' | 'extracting' | 'review';

export interface ThoughtCard {
  id: string;
  title: string;
  body: string;
}

interface CaptureState {
  phase: CapturePhase;
  transcript: string;
  cards: ThoughtCard[];
  error: string | null;

  // Actions
  setPhase: (phase: CapturePhase) => void;
  setTranscript: (transcript: string) => void;
  setCards: (cards: ThoughtCard[]) => void;
  setError: (error: string | null) => void;
  updateCard: (id: string, updates: Partial<ThoughtCard>) => void;
  removeCard: (id: string) => void;
  reorderCards: (oldIndex: number, newIndex: number) => void;
  reset: () => void;
}

const initialState = {
  phase: 'idle' as CapturePhase,
  transcript: '',
  cards: [],
  error: null,
};

export const useCaptureStore = create<CaptureState>((set) => ({
  ...initialState,

  setPhase: (phase) => set({ phase }),

  setTranscript: (transcript) => set({ transcript }),

  setCards: (cards) => set({ cards }),

  setError: (error) => set({ error }),

  updateCard: (id, updates) =>
    set((state) => ({
      cards: state.cards.map((card) =>
        card.id === id ? { ...card, ...updates } : card
      ),
    })),

  removeCard: (id) =>
    set((state) => ({
      cards: state.cards.filter((card) => card.id !== id),
    })),

  reorderCards: (oldIndex, newIndex) =>
    set((state) => {
      const newCards = [...state.cards];
      const [removed] = newCards.splice(oldIndex, 1);
      newCards.splice(newIndex, 0, removed);
      return { cards: newCards };
    }),

  reset: () => set(initialState),
}));
