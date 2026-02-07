import { create } from 'zustand';
import type { Scaffold as MindMapScaffold } from '@/components/WritingModes/MindMap/types';

export interface ScaffoldSection {
  id: string;
  title: string;
  type: string;
  suggested_topic_sentence?: string;
  hints?: string[];
  order: number;
  status: 'empty' | 'in-progress' | 'complete';
}

interface ScaffoldState {
  topic: string;
  sections: ScaffoldSection[];
  isLoading: boolean;
  setTopic: (topic: string) => void;
  setSections: (sections: Omit<ScaffoldSection, 'status'>[]) => void;
  updateSectionStatus: (id: string, status: ScaffoldSection['status']) => void;
  importFromMindMap: (scaffold: MindMapScaffold) => void;
  clearScaffold: () => void;
}

export const useScaffoldStore = create<ScaffoldState>((set) => ({
  topic: '',
  sections: [],
  isLoading: false,

  setTopic: (topic) => set({ topic }),

  setSections: (sections) =>
    set({
      sections: sections.map((s) => ({
        ...s,
        status: 'empty' as const,
      })),
    }),

  updateSectionStatus: (id, status) =>
    set((state) => ({
      sections: state.sections.map((s) =>
        s.id === id ? { ...s, status } : s
      ),
    })),

  importFromMindMap: (scaffold) => {
    const timestamp = Date.now();
    set({
      topic: scaffold.title,
      sections: scaffold.sections.map((s, i) => ({
        id: `mm-${i}-${timestamp}`,
        title: s.heading,
        type: 'body',
        suggested_topic_sentence: s.suggestedContent,
        hints: [s.hint],
        order: i,
        status: 'empty' as const,
      })),
    });
  },

  clearScaffold: () =>
    set({
      topic: '',
      sections: [],
      isLoading: false,
    }),
}));
