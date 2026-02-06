import { create } from 'zustand';

export interface Correction {
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic';
  start: number;
  end: number;
  explanation?: string;
}

interface EditorState {
  content: string;
  corrections: Correction[];
  isSaving: boolean;
  setContent: (content: string) => void;
  setCorrections: (corrections: Correction[]) => void;
  clearCorrections: () => void;
  setIsSaving: (isSaving: boolean) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  content: '',
  corrections: [],
  isSaving: false,
  setContent: (content) => set({ content }),
  setCorrections: (corrections) => set({ corrections }),
  clearCorrections: () => set({ corrections: [] }),
  setIsSaving: (isSaving) => set({ isSaving }),
}));
