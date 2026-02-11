/**
 * Coach Store
 *
 * Manages AI Coach chat message state, per-document.
 */

import { create } from 'zustand';
import type { Correction } from './editorStore';

export interface CoachMessage {
  id: string;
  role: 'user' | 'coach';
  content: string;
  timestamp: number;
}

/** Per-document coach data (all in-memory, not persisted) */
interface DocumentCoachData {
  messages: CoachMessage[];
  isLoading: boolean;
}

interface CoachState {
  messages: CoachMessage[];
  isLoading: boolean;
  pendingExplainCorrection: Correction | null;

  // Per-document storage
  _documentSessions: Record<string, DocumentCoachData>;
  _activeDocumentId: string | null;

  addMessage: (role: 'user' | 'coach', content: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
  requestExplanation: (correction: Correction) => void;
  clearPendingExplanation: () => void;

  // Per-document
  setActiveDocument: (docId: string) => void;
  deleteDocumentSession: (docId: string) => void;
}

let nextId = 0;

function emptySession(): DocumentCoachData {
  return { messages: [], isLoading: false };
}

export const useCoachStore = create<CoachState>()((set, get) => ({
  messages: [],
  isLoading: false,
  pendingExplainCorrection: null,
  _documentSessions: {},
  _activeDocumentId: null,

  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `coach-${++nextId}`,
          role,
          content,
          timestamp: Date.now(),
        },
      ],
    })),

  setLoading: (isLoading) => set({ isLoading }),

  requestExplanation: (correction) => set({ pendingExplainCorrection: correction }),

  clearPendingExplanation: () => set({ pendingExplainCorrection: null }),

  clearMessages: () => {
    const state = get();
    const nextSessions = { ...state._documentSessions };
    if (state._activeDocumentId) {
      delete nextSessions[state._activeDocumentId];
    }
    set({ messages: [], isLoading: false, _documentSessions: nextSessions });
  },

  setActiveDocument: (docId: string) => {
    const state = get();
    const oldDocId = state._activeDocumentId;

    if (oldDocId === docId) return;

    // Save current working copy for old document
    const nextSessions = { ...state._documentSessions };
    if (oldDocId) {
      nextSessions[oldDocId] = {
        messages: state.messages,
        isLoading: state.isLoading,
      };
    }

    // Load data for new document (or fresh defaults)
    const docData = nextSessions[docId] ?? emptySession();

    set({
      _activeDocumentId: docId,
      _documentSessions: nextSessions,
      messages: docData.messages,
      isLoading: docData.isLoading,
    });
  },

  deleteDocumentSession: (docId: string) => {
    set((state) => {
      const nextSessions = { ...state._documentSessions };
      delete nextSessions[docId];
      return { _documentSessions: nextSessions };
    });
  },
}));

// --- Subscribe to document store changes ---
let _coachDocStoreSubscribed = false;
let _coachLastDocIds: Set<string> | null = null;

function ensureCoachDocSubscription() {
  if (_coachDocStoreSubscribed) return;
  _coachDocStoreSubscribed = true;

  import('./documentStore').then(({ useDocumentStore }) => {
    const docState = useDocumentStore.getState();
    if (docState.activeDocumentId) {
      useCoachStore.getState().setActiveDocument(docState.activeDocumentId);
    }
    _coachLastDocIds = new Set(docState.documents.map((d) => d.id));

    useDocumentStore.subscribe((state, prevState) => {
      if (state.activeDocumentId && state.activeDocumentId !== prevState.activeDocumentId) {
        useCoachStore.getState().setActiveDocument(state.activeDocumentId);
      }

      const currentIds = new Set(state.documents.map((d) => d.id));
      if (_coachLastDocIds) {
        for (const id of _coachLastDocIds) {
          if (!currentIds.has(id)) {
            useCoachStore.getState().deleteDocumentSession(id);
          }
        }
      }
      _coachLastDocIds = currentIds;
    });
  });
}

setTimeout(ensureCoachDocSubscription, 0);
