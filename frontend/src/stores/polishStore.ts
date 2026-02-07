/**
 * Polish Store
 *
 * State management for Polish Mode suggestions and deep analysis
 */

import { create } from 'zustand';

export interface TrackedChange {
  id: string;
  type: 'insert' | 'delete' | 'replace';
  start: number;
  end: number;
  text: string;        // new text for insert/replace
  original?: string;   // original text for delete/replace
  category: string;    // spelling, grammar, style, clarity
  explanation: string;
  isApplied?: boolean;
  isDismissed?: boolean;
}

interface PolishState {
  suggestions: TrackedChange[];
  isAnalyzing: boolean;
  activeSuggestion: string | null;

  setSuggestions: (suggestions: TrackedChange[]) => void;
  applySuggestion: (id: string) => void;
  dismissSuggestion: (id: string) => void;
  clearSuggestions: () => void;
  setActiveSuggestion: (id: string | null) => void;
  setIsAnalyzing: (isAnalyzing: boolean) => void;
}

export const usePolishStore = create<PolishState>((set) => ({
  suggestions: [],
  isAnalyzing: false,
  activeSuggestion: null,

  setSuggestions: (suggestions) => set({ suggestions }),

  applySuggestion: (id) =>
    set((state) => ({
      suggestions: state.suggestions.map((s) =>
        s.id === id ? { ...s, isApplied: true } : s
      )
    })),

  dismissSuggestion: (id) =>
    set((state) => ({
      suggestions: state.suggestions.map((s) =>
        s.id === id ? { ...s, isDismissed: true } : s
      )
    })),

  clearSuggestions: () => set({ suggestions: [], activeSuggestion: null }),

  setActiveSuggestion: (id) => set({ activeSuggestion: id }),

  setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing })
}));
