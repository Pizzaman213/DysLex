/**
 * Zustand store for Capture Mode state management.
 * Per-document sessions: each document gets its own capture data.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
// switched to per-user scoped storage — connor secrist 02-09
import { createUserScopedStorage, registerScopedStore } from '@/services/userScopedStorage';

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

/** Persisted per-document capture data */
interface DocumentCaptureData {
  transcript: string;
  cards: ThoughtCard[];
  takes: number;
  brainstormAutoProbe: boolean;
}

/** Transient (in-memory only) per-document data */
interface TransientCaptureData {
  phase: CapturePhase;
  error: string | null;
  audioBlobs: Blob[];
  audioUrls: string[];
  lastExtractedOffset: number;
  isIncrementalExtracting: boolean;
  brainstormActive: boolean;
}

interface CaptureState {
  // Working copy (active document)
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

  // Per-document storage
  sessions: Record<string, DocumentCaptureData>;
  _transientSession: Record<string, TransientCaptureData>;
  _activeDocumentId: string | null;

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

  // Per-document
  setActiveDocument: (docId: string) => void;
  deleteDocumentSession: (docId: string) => void;

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

function emptyDocumentData(): DocumentCaptureData {
  return {
    transcript: '',
    cards: [],
    takes: 0,
    brainstormAutoProbe: true,
  };
}

function emptyTransientData(): TransientCaptureData {
  return {
    phase: 'idle',
    error: null,
    audioBlobs: [],
    audioUrls: [],
    lastExtractedOffset: 0,
    isIncrementalExtracting: false,
    brainstormActive: false,
  };
}

/** Derive phase from persisted data (same logic as the old merge function) */
function derivePhase(data: DocumentCaptureData): CapturePhase {
  if (data.cards.length > 0) return 'review';
  if (data.transcript.trim()) return 'recorded';
  return 'idle';
}

export const useCaptureStore = create<CaptureState>()(
  persist(
    (set, get) => ({
      ...initialState,
      sessions: {},
      _transientSession: {},
      _activeDocumentId: null,

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

      setActiveDocument: (docId: string) => {
        const state = get();
        const oldDocId = state._activeDocumentId;

        if (oldDocId === docId) return;

        // Save current working copy for old document
        const nextSessions = { ...state.sessions };
        const nextTransient = { ...state._transientSession };

        if (oldDocId) {
          nextSessions[oldDocId] = {
            transcript: state.transcript,
            cards: state.cards,
            takes: state.takes,
            brainstormAutoProbe: state.brainstormAutoProbe,
          };
          nextTransient[oldDocId] = {
            phase: state.phase,
            error: state.error,
            audioBlobs: state.audioBlobs,
            audioUrls: state.audioUrls,
            lastExtractedOffset: state.lastExtractedOffset,
            isIncrementalExtracting: state.isIncrementalExtracting,
            brainstormActive: state.brainstormActive,
          };
        }

        // Load data for new document (or fresh defaults)
        const docData = nextSessions[docId] ?? emptyDocumentData();
        const transientData = nextTransient[docId] ?? emptyTransientData();

        // Derive phase if transient data is fresh (no saved phase)
        const phase = nextTransient[docId]
          ? transientData.phase
          : derivePhase(docData);

        set({
          _activeDocumentId: docId,
          sessions: nextSessions,
          _transientSession: nextTransient,
          transcript: docData.transcript,
          cards: docData.cards,
          takes: docData.takes,
          brainstormAutoProbe: docData.brainstormAutoProbe,
          phase,
          error: transientData.error,
          audioBlobs: transientData.audioBlobs,
          audioUrls: transientData.audioUrls,
          lastExtractedOffset: transientData.lastExtractedOffset,
          isIncrementalExtracting: transientData.isIncrementalExtracting,
          brainstormActive: transientData.brainstormActive,
        });
      },

      deleteDocumentSession: (docId: string) => {
        set((state) => {
          const nextSessions = { ...state.sessions };
          const nextTransient = { ...state._transientSession };
          // Revoke audio URLs for the deleted document
          if (nextTransient[docId]?.audioUrls) {
            nextTransient[docId].audioUrls.forEach((url) => URL.revokeObjectURL(url));
          }
          delete nextSessions[docId];
          delete nextTransient[docId];
          return { sessions: nextSessions, _transientSession: nextTransient };
        });
      },

      reset: () =>
        set((state) => {
          state.audioUrls.forEach((url) => URL.revokeObjectURL(url));

          // Clear persisted session for active document
          const nextSessions = { ...state.sessions };
          const nextTransient = { ...state._transientSession };
          const activeId = state._activeDocumentId;
          if (activeId) {
            delete nextSessions[activeId];
            delete nextTransient[activeId];
          }

          return {
            ...initialState,
            sessions: nextSessions,
            _transientSession: nextTransient,
            _activeDocumentId: state._activeDocumentId,
          };
        }),
    }),
    {
      name: 'dyslex-capture-session',
      storage: createUserScopedStorage(),
      skipHydration: true,
      version: 1,
      partialize: (state) => {
        // Flush working copy into sessions before serializing
        const sessions = { ...state.sessions };
        if (state._activeDocumentId) {
          sessions[state._activeDocumentId] = {
            transcript: state.transcript,
            cards: state.cards,
            takes: state.takes,
            brainstormAutoProbe: state.brainstormAutoProbe,
          };
        }
        return {
          sessions,
          _activeDocumentId: state._activeDocumentId,
        };
      },
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        const activeId = state._activeDocumentId;
        if (activeId && state.sessions[activeId]) {
          const docData = state.sessions[activeId];
          state.transcript = docData.transcript;
          state.cards = docData.cards;
          state.takes = docData.takes;
          state.brainstormAutoProbe = docData.brainstormAutoProbe;
          state.phase = derivePhase(docData);
        }
      },
      migrate: (persisted: any, version: number) => {
        if (version < 1) {
          // Migrate from v0 (top-level transcript/cards/takes) to v1 (per-document sessions)
          const state = persisted as any;
          const DEFAULT_DOC_ID = '00000000-0000-4000-8000-000000000001';

          const docData: DocumentCaptureData = {
            transcript: state.transcript || '',
            cards: state.cards || [],
            takes: state.takes || 0,
            brainstormAutoProbe: state.brainstormAutoProbe ?? true,
          };

          state.sessions = { [DEFAULT_DOC_ID]: docData };
          state._activeDocumentId = DEFAULT_DOC_ID;

          // Clean up old top-level fields
          delete state.transcript;
          delete state.cards;
          delete state.takes;
          delete state.brainstormAutoProbe;
        }
        return persisted;
      },
    },
  ),
);

registerScopedStore(() => useCaptureStore.persist.rehydrate());

// --- Subscribe to document store changes ---
let _captureDocStoreSubscribed = false;
let _captureLastDocIds: Set<string> | null = null;

function ensureCaptureDocSubscription() {
  if (_captureDocStoreSubscribed) return;
  _captureDocStoreSubscribed = true;

  import('./documentStore').then(({ useDocumentStore }) => {
    const docState = useDocumentStore.getState();
    if (docState.activeDocumentId) {
      useCaptureStore.getState().setActiveDocument(docState.activeDocumentId);
    }
    _captureLastDocIds = new Set(docState.documents.map((d) => d.id));

    useDocumentStore.subscribe((state, prevState) => {
      if (state.activeDocumentId && state.activeDocumentId !== prevState.activeDocumentId) {
        useCaptureStore.getState().setActiveDocument(state.activeDocumentId);
      }

      const currentIds = new Set(state.documents.map((d) => d.id));
      if (_captureLastDocIds) {
        for (const id of _captureLastDocIds) {
          if (!currentIds.has(id)) {
            useCaptureStore.getState().deleteDocumentSession(id);
          }
        }
      }
      _captureLastDocIds = currentIds;
    });
  });
}

setTimeout(ensureCaptureDocSubscription, 0);
