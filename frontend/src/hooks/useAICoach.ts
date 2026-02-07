import { useEffect, useState, useRef } from 'react';
import { Editor } from '@tiptap/react';
import { useScaffoldStore } from '../stores/scaffoldStore';
import { useSessionStore } from '../stores/sessionStore';

export interface CoachNudge {
  id: string;
  message: string;
  type: 'section' | 'transition' | 'milestone' | 'idle' | 'completion';
}

const NUDGE_COOLDOWN = 30000; // 30 seconds between nudges
const IDLE_THRESHOLD = 60000; // 60 seconds of no typing
const WORD_COUNT_MILESTONES = [100, 250, 500, 750, 1000];
const INTERVENTION_SPACING = 120000; // 2 minutes between any intervention

export function useAICoach(editor: Editor | null) {
  const [currentNudge, setCurrentNudge] = useState<CoachNudge | null>(null);
  const [dismissedNudges, setDismissedNudges] = useState<Set<string>>(new Set());
  const { sections } = useScaffoldStore();

  const lastNudgeTimeRef = useRef(0);
  const lastActivityTimeRef = useRef(Date.now());
  const lastWordCountRef = useRef(0);
  const celebratedMilestonesRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (!editor) return;

    // Track typing activity
    const handleUpdate = () => {
      lastActivityTimeRef.current = Date.now();
    };

    editor.on('update', handleUpdate);

    // Check for nudge opportunities every 10 seconds
    const intervalId = setInterval(() => {
      checkForNudges();
    }, 10000);

    return () => {
      editor.off('update', handleUpdate);
      clearInterval(intervalId);
    };
  }, [editor, sections]);

  const checkForNudges = () => {
    if (!editor) return;

    const now = Date.now();

    // Enforce cooldown
    if (now - lastNudgeTimeRef.current < NUDGE_COOLDOWN) {
      return;
    }

    // Check for recent check-in to avoid overlapping interventions
    const lastCheckInTime = useSessionStore.getState().lastCheckInTime;
    if (lastCheckInTime && now - lastCheckInTime < INTERVENTION_SPACING) {
      return;
    }

    const wordCount = editor.storage.characterCount?.words() || 0;
    const idleTime = now - lastActivityTimeRef.current;

    // Priority order: completion > milestone > section > idle > transition

    // 1. Completion celebration
    if (sections.length > 0) {
      const allComplete = sections.every((s) => s.status === 'complete');
      const nudgeId = 'completion-all';

      if (allComplete && !dismissedNudges.has(nudgeId)) {
        showNudge({
          id: nudgeId,
          message: "🎉 You've completed all sections! Great work on your essay.",
          type: 'completion',
        });
        return;
      }
    }

    // 2. Word count milestones
    for (const milestone of WORD_COUNT_MILESTONES) {
      if (
        wordCount >= milestone &&
        lastWordCountRef.current < milestone &&
        !celebratedMilestonesRef.current.has(milestone)
      ) {
        const nudgeId = `milestone-${milestone}`;
        if (!dismissedNudges.has(nudgeId)) {
          celebratedMilestonesRef.current.add(milestone);
          showNudge({
            id: nudgeId,
            message: `🎯 ${milestone} words! You're making great progress.`,
            type: 'milestone',
          });
          return;
        }
      }
    }

    // 3. Section completion prompts
    if (sections.length > 0) {
      const currentSection = sections.find((s) => s.status === 'in-progress');
      const nextSection = sections.find((s) => s.status === 'empty');

      if (currentSection && wordCount > lastWordCountRef.current + 20) {
        const nudgeId = `section-${currentSection.id}`;
        if (!dismissedNudges.has(nudgeId)) {
          showNudge({
            id: nudgeId,
            message: `Keep going on "${currentSection.title}" — you're making good progress!`,
            type: 'section',
          });
          return;
        }
      }

      if (nextSection && !currentSection) {
        const nudgeId = `section-next-${nextSection.id}`;
        if (!dismissedNudges.has(nudgeId)) {
          showNudge({
            id: nudgeId,
            message: `Ready to start "${nextSection.title}"?`,
            type: 'section',
          });
          return;
        }
      }
    }

    // 4. Idle encouragement
    if (idleTime >= IDLE_THRESHOLD && wordCount > 0) {
      const nudgeId = 'idle-encouragement';
      if (!dismissedNudges.has(nudgeId)) {
        const messages = [
          "Take your time — there's no rush. Keep going when you're ready.",
          'Every word counts. Take a breath and continue when ready.',
          "You're doing great. Ready to add a bit more?",
        ];
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];

        showNudge({
          id: nudgeId,
          message: randomMessage,
          type: 'idle',
        });
        return;
      }
    }

    // 5. Transition suggestions (lower priority)
    if (sections.length > 1 && wordCount > lastWordCountRef.current + 30) {
      const nudgeId = 'transition-suggestion';
      if (!dismissedNudges.has(nudgeId)) {
        showNudge({
          id: nudgeId,
          message: 'Consider adding a transition to connect your ideas smoothly.',
          type: 'transition',
        });
        return;
      }
    }

    lastWordCountRef.current = wordCount;
  };

  const showNudge = (nudge: CoachNudge) => {
    setCurrentNudge(nudge);
    lastNudgeTimeRef.current = Date.now();

    // Record intervention time in sessionStore
    useSessionStore.setState({ lastInterventionTime: Date.now() });
  };

  const dismissNudge = (nudgeId: string) => {
    setCurrentNudge(null);
    setDismissedNudges((prev) => new Set(prev).add(nudgeId));
  };

  return {
    currentNudge,
    dismissNudge,
  };
}
