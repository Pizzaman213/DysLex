/**
 * Zustand store for Capture Mode state management.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type CapturePhase = 'idle' | 'recording' | 'recorded' | 'transcribing' | 'extracting' | 'review' | 'brainstorming';

export interface SubIdea {
  id: string;
  title: string;
  body: string;
}

export interface ThoughtCard {
  id: string;
  title: string;
  body: string;
  sub_ideas: SubIdea[];
}

interface CaptureState {
  phase: CapturePhase;
  transcript: string;
  cards: ThoughtCard[];
  error: string | null;
  takes: number;
  /** In-memory only — audio blobs from recordings (not persisted) */
  audioBlobs: Blob[];
  /** Object URLs for audio playback (not persisted) */
  audioUrls: string[];
  /** Character offset of last incremental extraction */
  lastExtractedOffset: number;
  /** Whether an incremental extraction is running */
  isIncrementalExtracting: boolean;
  /** Whether brainstorm loop is active (transient, not persisted) */
  brainstormActive: boolean;
  /** Whether AI auto-probes after pauses (persisted preference) */
  brainstormAutoProbe: boolean;

  // Actions
  setPhase: (phase: CapturePhase) => void;
  setTranscript: (transcript: string) => void;
  appendTranscript: (text: string) => void;
  setCards: (cards: ThoughtCard[]) => void;
  appendCards: (newCards: ThoughtCard[]) => void;
  setError: (error: string | null) => void;
  updateCard: (id: string, updates: Partial<ThoughtCard>) => void;
  removeCard: (id: string) => void;
  reorderCards: (oldIndex: number, newIndex: number) => void;
  incrementTakes: () => void;
  addAudioBlob: (blob: Blob) => void;
  clearAudioBlobs: () => void;
  setLastExtractedOffset: (offset: number) => void;
  setIncrementalExtracting: (v: boolean) => void;

  // Sub-idea actions
  updateSubIdea: (cardId: string, subId: string, updates: Partial<SubIdea>) => void;
  removeSubIdea: (cardId: string, subId: string) => void;
  addSubIdea: (cardId: string) => void;

  // Brainstorm actions
  setBrainstormActive: (active: boolean) => void;
  setBrainstormAutoProbe: (enabled: boolean) => void;

  reset: () => void;
}

const initialState = {
  phase: 'idle' as CapturePhase,
  transcript: '',
  cards: [] as ThoughtCard[],
  error: null as string | null,
  takes: 0,
  audioBlobs: [] as Blob[],
  audioUrls: [] as string[],
  lastExtractedOffset: 0,
  isIncrementalExtracting: false,
  brainstormActive: false,
  brainstormAutoProbe: true,
};

export const useCaptureStore = create<CaptureState>()(
  persist(
    (set) => ({
      ...initialState,

      setPhase: (phase) => set({ phase }),

      setTranscript: (transcript) => set({ transcript }),

      appendTranscript: (text) =>
        set((state) => ({
          transcript: state.transcript
            ? state.transcript.trimEnd() + ' ' + text.trimStart()
            : text,
        })),

      setCards: (cards) => set({ cards }),

      appendCards: (newCards) =>
        set((state) => {
          const existingTitles = new Set(
            state.cards.map((c) => c.title.toLowerCase().trim()),
          );
          const deduped = newCards.filter(
            (c) => !existingTitles.has(c.title.toLowerCase().trim()),
          );
          return { cards: [...state.cards, ...deduped] };
        }),

      setError: (error) => set({ error }),

      updateCard: (id, updates) =>
        set((state) => ({
          cards: state.cards.map((card) =>
            card.id === id ? { ...card, ...updates } : card,
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

      incrementTakes: () =>
        set((state) => ({ takes: state.takes + 1 })),

      addAudioBlob: (blob) =>
        set((state) => ({
          audioBlobs: [...state.audioBlobs, blob],
          audioUrls: [...state.audioUrls, URL.createObjectURL(blob)],
        })),

      clearAudioBlobs: () =>
        set((state) => {
          state.audioUrls.forEach((url) => URL.revokeObjectURL(url));
          return { audioBlobs: [], audioUrls: [] };
        }),

      setLastExtractedOffset: (offset) => set({ lastExtractedOffset: offset }),

      setIncrementalExtracting: (v) => set({ isIncrementalExtracting: v }),

      // Sub-idea actions
      updateSubIdea: (cardId, subId, updates) =>
        set((state) => ({
          cards: state.cards.map((card) =>
            card.id === cardId
              ? {
                  ...card,
                  sub_ideas: card.sub_ideas.map((sub) =>
                    sub.id === subId ? { ...sub, ...updates } : sub,
                  ),
                }
              : card,
          ),
        })),

      removeSubIdea: (cardId, subId) =>
        set((state) => ({
          cards: state.cards.map((card) =>
            card.id === cardId
              ? {
                  ...card,
                  sub_ideas: card.sub_ideas.filter((sub) => sub.id !== subId),
                }
              : card,
          ),
        })),

      addSubIdea: (cardId) =>
        set((state) => ({
          cards: state.cards.map((card) => {
            if (card.id !== cardId) return card;
            const idx = card.sub_ideas.length + 1;
            const newSub: SubIdea = {
              id: `${card.id}-sub-${idx}`,
              title: '',
              body: '',
            };
            return { ...card, sub_ideas: [...card.sub_ideas, newSub] };
          }),
        })),

      // Brainstorm actions
      setBrainstormActive: (active) => set({ brainstormActive: active }),
      setBrainstormAutoProbe: (enabled) => set({ brainstormAutoProbe: enabled }),

      reset: () =>
        set((state) => {
          state.audioUrls.forEach((url) => URL.revokeObjectURL(url));
          return { ...initialState };
        }),
    }),
    {
      name: 'dyslex-capture-session',
      partialize: (state) => ({
        transcript: state.transcript,
        cards: state.cards,
        takes: state.takes,
        brainstormAutoProbe: state.brainstormAutoProbe,
      }),
      merge: (persisted, current) => {
        const saved = persisted as Partial<CaptureState> | undefined;
        if (!saved) return current;

        // Compute phase from persisted data
        let phase: CapturePhase = 'idle';
        if (saved.cards && saved.cards.length > 0) {
          phase = 'review';
        } else if (saved.transcript && saved.transcript.trim()) {
          phase = 'recorded';
        }

        return {
          ...current,
          transcript: saved.transcript || '',
          cards: saved.cards || [],
          takes: saved.takes || 0,
          brainstormAutoProbe: saved.brainstormAutoProbe ?? true,
          phase,
        };
      },
    },
  ),
);
