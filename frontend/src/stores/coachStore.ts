/**
 * Coach Store
 *
 * Manages AI Coach chat message state
 */

import { create } from 'zustand';

export interface CoachMessage {
  id: string;
  role: 'user' | 'coach';
  content: string;
  timestamp: number;
}

interface CoachState {
  messages: CoachMessage[];
  isLoading: boolean;

  addMessage: (role: 'user' | 'coach', content: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

let nextId = 0;

export const useCoachStore = create<CoachState>()((set) => ({
  messages: [],
  isLoading: false,

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

  clearMessages: () => set({ messages: [], isLoading: false }),
}));
