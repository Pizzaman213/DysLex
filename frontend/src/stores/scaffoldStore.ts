import { create } from 'zustand';

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

  clearScaffold: () =>
    set({
      topic: '',
      sections: [],
      isLoading: false,
    }),
}));
