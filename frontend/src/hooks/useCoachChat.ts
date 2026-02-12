/**
 * useCoachChat — sends messages to the AI coach and manages state
 */

import { useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { api } from '../services/api';
import { useCoachStore } from '../stores/coachStore';
import { useSessionStore } from '../stores/sessionStore';
import { useEditorStore, Correction } from '../stores/editorStore';
import { useMindMapStore } from '../stores/mindMapStore';

export function useCoachChat(editor: Editor | null) {
  const { addMessage, setLoading } = useCoachStore();
  const { totalWordsWritten, correctionsApplied, getTimeSpent } = useSessionStore();

  const sendMessage = useCallback(
    async (text: string, focusedCorrection?: Correction) => {
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

        // Gather active corrections for context
        const allCorrections = useEditorStore.getState().corrections;
        const activeCorrections = allCorrections
          .filter((c) => !c.isApplied && !c.isDismissed)
          .slice(0, 10)
          .map((c) => ({
            original: c.original,
            suggested: c.suggested,
            type: c.type,
            explanation: c.explanation,
          }));

        const correctionsContext = activeCorrections.length > 0 || focusedCorrection
          ? {
              active_corrections: activeCorrections,
              focused_correction: focusedCorrection
                ? {
                    original: focusedCorrection.original,
                    suggested: focusedCorrection.suggested,
                    type: focusedCorrection.type,
                    explanation: focusedCorrection.explanation,
                  }
                : null,
            }
          : undefined;

        // Gather mind map context
        const mindMapState = useMindMapStore.getState();
        const { nodes, edges, clusterNames } = mindMapState;
        const rootNode = nodes.find((n) => n.id === 'root');
        const nonRootNodes = nodes.filter((n) => n.id !== 'root');

        const mindMapContext = nonRootNodes.length > 0
          ? {
              central_idea: rootNode?.data.title || null,
              ideas: nonRootNodes.slice(0, 20).map((n) => ({
                title: n.data.title,
                body: n.data.body || null,
                theme: clusterNames[n.data.cluster] || null,
              })),
              connections: edges.slice(0, 15).map((e) => {
                const sourceNode = nodes.find((n) => n.id === e.source);
                const targetNode = nodes.find((n) => n.id === e.target);
                return {
                  from_idea: sourceNode?.data.title || e.source,
                  to_idea: targetNode?.data.title || e.target,
                  relationship: e.data?.relationship || null,
                };
              }),
              themes: Object.values(clusterNames).filter(
                (name) => !name.startsWith('Cluster ')
              ),
            }
          : undefined;

        const response = await api.coachChat(text, writingContext, sessionStats, correctionsContext, mindMapContext);
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
