import { create } from 'zustand';
import type { Editor } from '@tiptap/react';

export interface Correction {
  id: string;
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic' | 'homophone' | 'clarity' | 'style';
  start: number;
  end: number;
  explanation?: string;
  isApplied?: boolean;
  isDismissed?: boolean;
}

interface EditorState {
  content: string;
  corrections: Correction[];
  isSaving: boolean;
  activeCorrection: string | null;
  editorInstance: Editor | null;
  setContent: (content: string) => void;
  setCorrections: (corrections: Correction[]) => void;
  clearCorrections: () => void;
  setIsSaving: (isSaving: boolean) => void;
  applyCorrection: (id: string) => void;
  dismissCorrection: (id: string) => void;
  applyAllCorrections: () => void;
  setActiveCorrection: (id: string | null) => void;
  setEditorInstance: (editor: Editor | null) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  content: '',
  corrections: [],
  isSaving: false,
  activeCorrection: null,
  editorInstance: null,
  setContent: (content) => set({ content }),
  setCorrections: (corrections) => set({ corrections }),
  clearCorrections: () => set({ corrections: [] }),
  setIsSaving: (isSaving) => set({ isSaving }),
  applyCorrection: (id) =>
    set((state) => ({
      corrections: state.corrections.map((c) =>
        c.id === id ? { ...c, isApplied: true } : c
      ),
    })),
  dismissCorrection: (id) =>
    set((state) => ({
      corrections: state.corrections.map((c) =>
        c.id === id ? { ...c, isDismissed: true } : c
      ),
    })),
  applyAllCorrections: () =>
    set((state) => ({
      corrections: state.corrections.map((c) =>
        c.isApplied || c.isDismissed ? c : { ...c, isApplied: true }
      ),
    })),
  setActiveCorrection: (id) => set({ activeCorrection: id }),
  setEditorInstance: (editor) => set({ editorInstance: editor }),
}));
