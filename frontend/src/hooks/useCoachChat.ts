/**
 * useCoachChat — sends messages to the AI coach and manages state
 */

import { useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { api } from '../services/api';
import { useCoachStore } from '../stores/coachStore';
import { useSessionStore } from '../stores/sessionStore';

export function useCoachChat(editor: Editor | null) {
  const { addMessage, setLoading } = useCoachStore();
  const { totalWordsWritten, correctionsApplied, getTimeSpent } = useSessionStore();

  const sendMessage = useCallback(
    async (text: string) => {
      addMessage('user', text);
      setLoading(true);

      try {
        // Gather context from the editor and session
        const writingContext = editor?.getText()?.slice(0, 3000) || undefined;
        const sessionStats = {
          totalWordsWritten,
          timeSpent: getTimeSpent(),
          correctionsApplied,
        };

        const response = await api.coachChat(text, writingContext, sessionStats);
        const reply = response.data?.reply || "I'm here to help! Tell me more about what you're working on.";
        addMessage('coach', reply);
      } catch {
        addMessage(
          'coach',
          "Sorry, I couldn't connect right now. Try again in a moment!",
        );
      } finally {
        setLoading(false);
      }
    },
    [editor, addMessage, setLoading, totalWordsWritten, correctionsApplied, getTimeSpent],
  );

  return { sendMessage };
}
