/**
 * Central orchestration hook for voice-to-voice AI brainstorming.
 *
 * State machine:
 *   IDLE → LISTENING → PAUSE_DETECTED → AI_THINKING → AI_SPEAKING → LISTENING
 *                           |                               |
 *                           v                               v
 *                      WAITING_MANUAL                 (user interrupts)
 *                           |                               |
 *                           v                               v
 *                      (Ask AI btn)                     LISTENING
 *
 * Composes useCaptureVoice (mic) and useReadAloud (TTS).
 */

import { useReducer, useRef, useCallback, useEffect } from 'react';
import { useCaptureStore } from '../stores/captureStore';
import { api } from '../services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LoopState =
  | 'idle'
  | 'listening'
  | 'pause_detected'
  | 'ai_thinking'
  | 'ai_speaking'
  | 'waiting_manual';

interface ConversationEntry {
  role: 'user' | 'ai';
  content: string;
  timestamp: number;
}

interface State {
  loopState: LoopState;
  conversationHistory: ConversationEntry[];
  currentUtterance: string;
  aiResponse: string | null;
}

type Action =
  | { type: 'START' }
  | { type: 'STOP' }
  | { type: 'SET_STATE'; state: LoopState }
  | { type: 'SET_UTTERANCE'; text: string }
  | { type: 'AI_REPLY'; reply: string }
  | { type: 'ADD_TURN'; entry: ConversationEntry }
  | { type: 'RESET' };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'START':
      return { ...state, loopState: 'listening', aiResponse: null };
    case 'STOP':
      return { ...state, loopState: 'idle', currentUtterance: '', aiResponse: null };
    case 'SET_STATE':
      return { ...state, loopState: action.state };
    case 'SET_UTTERANCE':
      return { ...state, currentUtterance: action.text };
    case 'AI_REPLY':
      return { ...state, aiResponse: action.reply };
    case 'ADD_TURN':
      return {
        ...state,
        conversationHistory: [...state.conversationHistory, action.entry],
      };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

const initialState: State = {
  loopState: 'idle',
  conversationHistory: [],
  currentUtterance: '',
  aiResponse: null,
};

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const DEFAULT_PAUSE_MS = 3000;
const MIN_WORDS_FOR_TRIGGER = 5;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/** Voice interface expected by the brainstorm loop. */
export interface BrainstormVoice {
  transcript: string;
  isRecording: boolean;
  start: () => Promise<void>;
  stop: () => Promise<string>;
  resetTranscript: () => void;
}

export interface UseBrainstormLoopReturn {
  loopState: LoopState;
  isActive: boolean;
  conversationHistory: ConversationEntry[];
  currentUtterance: string;
  aiResponse: string | null;
  startBrainstorm: () => Promise<void>;
  stopBrainstorm: () => void;
  triggerAiTurn: () => void;
  interruptAi: () => void;
}

/**
 * @param voice - The shared voice instance from CaptureMode.
 *   Chrome only allows one active SpeechRecognition at a time,
 *   so the brainstorm loop MUST reuse CaptureMode's voice instance.
 */
export function useBrainstormLoop(voice: BrainstormVoice): UseBrainstormLoopReturn {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Direct audio playback for MagpieTTS (bypasses voiceEnabled setting —
  // brainstorm is inherently voice-first and always needs TTS)
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const autoProbe = useCaptureStore((s) => s.brainstormAutoProbe);
  const cards = useCaptureStore((s) => s.cards);
  const transcript = useCaptureStore((s) => s.transcript);
  const appendCards = useCaptureStore((s) => s.appendCards);
  const updateCard = useCaptureStore((s) => s.updateCard);

  // Refs for mutable values across renders
  const pauseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTriggerOffsetRef = useRef(0);
  const conversationRef = useRef<ConversationEntry[]>([]);
  const loopStateRef = useRef<LoopState>('idle');
  const aiSpeakingRef = useRef(false);

  // Keep refs in sync
  useEffect(() => {
    conversationRef.current = state.conversationHistory;
  }, [state.conversationHistory]);

  useEffect(() => {
    loopStateRef.current = state.loopState;
  }, [state.loopState]);

  // -------------------------------------------------------------------------
  // Pause detection: watch transcript changes while listening
  // -------------------------------------------------------------------------

  useEffect(() => {
    // Only run pause detection while listening
    if (state.loopState !== 'listening') return;

    // Clear previous timer
    if (pauseTimerRef.current) {
      clearTimeout(pauseTimerRef.current);
      pauseTimerRef.current = null;
    }

    // Calculate current utterance (text since last AI trigger)
    const currentText = voice.transcript.slice(lastTriggerOffsetRef.current).trim();
    dispatch({ type: 'SET_UTTERANCE', text: currentText });

    const wordCount = currentText.split(/\s+/).filter(Boolean).length;
    if (wordCount < MIN_WORDS_FOR_TRIGGER) return;

    if (autoProbe) {
      pauseTimerRef.current = setTimeout(() => {
        if (loopStateRef.current === 'listening') {
          dispatch({ type: 'SET_STATE', state: 'pause_detected' });
        }
      }, DEFAULT_PAUSE_MS);
    }

    return () => {
      if (pauseTimerRef.current) {
        clearTimeout(pauseTimerRef.current);
        pauseTimerRef.current = null;
      }
    };
  }, [voice.transcript, state.loopState, autoProbe]);

  // -------------------------------------------------------------------------
  // Auto-trigger: when pause_detected, fire AI turn
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (state.loopState === 'pause_detected' && autoProbe) {
      fireAiTurn(state.currentUtterance);
    }
    // Manual mode: transition to waiting_manual
    if (state.loopState === 'pause_detected' && !autoProbe) {
      dispatch({ type: 'SET_STATE', state: 'waiting_manual' });
    }
  }, [state.loopState]); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // Interruption: if user speaks during AI_SPEAKING, stop TTS
  // -------------------------------------------------------------------------

  useEffect(() => {
    if (state.loopState === 'ai_speaking' && !aiSpeakingRef.current) return;

    // During AI speaking, watch for transcript changes indicating user is talking
    if (state.loopState === 'ai_speaking') {
      const currentText = voice.transcript.slice(lastTriggerOffsetRef.current).trim();
      if (currentText.length > 0) {
        // User started talking — interrupt audio playback
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }
        speechSynthesis.cancel();
        aiSpeakingRef.current = false;
        dispatch({ type: 'SET_STATE', state: 'listening' });
      }
    }
  }, [voice.transcript, state.loopState]);

  // -------------------------------------------------------------------------
  // Core: fire an AI turn
  // -------------------------------------------------------------------------

  const fireAiTurn = useCallback(async (utterance: string) => {
    if (!utterance.trim()) {
      console.log('[Brainstorm] Skipping empty utterance, returning to listening');
      dispatch({ type: 'SET_STATE', state: 'listening' });
      return;
    }

    console.log('[Brainstorm] Firing AI turn: %d chars, %d words', utterance.length, utterance.split(/\s+/).length);
    dispatch({ type: 'SET_STATE', state: 'ai_thinking' });

    // Record user turn
    const userEntry: ConversationEntry = {
      role: 'user',
      content: utterance,
      timestamp: Date.now(),
    };
    dispatch({ type: 'ADD_TURN', entry: userEntry });

    // Update trigger offset
    lastTriggerOffsetRef.current = voice.transcript.length;

    const startTime = performance.now();

    try {
      const existingCards = cards.map((c) => ({
        id: c.id,
        title: c.title,
        body: c.body,
      }));

      const history = [...conversationRef.current, userEntry].map((e) => ({
        role: e.role,
        content: e.content,
      }));

      console.log('[Brainstorm] API call: history=%d turns, cards=%d, transcript=%d chars', history.length, existingCards.length, transcript.length);

      const result = await api.brainstormTurn(
        utterance,
        history,
        existingCards,
        transcript,
      );

      const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
      console.log('[Brainstorm] AI replied in %ss: "%s"', elapsed, result.reply.slice(0, 100));

      // Record AI turn
      const aiEntry: ConversationEntry = {
        role: 'ai',
        content: result.reply,
        timestamp: Date.now(),
      };
      dispatch({ type: 'ADD_TURN', entry: aiEntry });
      dispatch({ type: 'AI_REPLY', reply: result.reply });

      // Handle new sub-ideas
      if (result.new_sub_ideas.length > 0 && result.suggested_parent_card_id) {
        console.log('[Brainstorm] Received %d sub-ideas for card %s', result.new_sub_ideas.length, result.suggested_parent_card_id);
        const parentCard = cards.find((c) => c.id === result.suggested_parent_card_id);
        if (parentCard) {
          const existingSubs = parentCard.sub_ideas || [];
          const newSubs = result.new_sub_ideas.filter(
            (s) => !existingSubs.some((es) => es.title.toLowerCase() === s.title.toLowerCase()),
          );
          if (newSubs.length > 0) {
            console.log('[Brainstorm] Adding %d new sub-ideas to card "%s"', newSubs.length, parentCard.title);
            updateCard(parentCard.id, {
              sub_ideas: [...existingSubs, ...newSubs],
            });
          }
        } else {
          console.warn('[Brainstorm] Parent card %s not found for sub-ideas', result.suggested_parent_card_id);
        }
      }

      // Handle new card
      if (result.suggested_new_card) {
        console.log('[Brainstorm] Creating new card: "%s"', result.suggested_new_card.title);
        appendCards([{
          ...result.suggested_new_card,
          sub_ideas: result.suggested_new_card.sub_ideas || [],
        }]);
      }

      // Speak the reply using MagpieTTS audio URL from backend
      if (loopStateRef.current !== 'idle') {
        dispatch({ type: 'SET_STATE', state: 'ai_speaking' });
        aiSpeakingRef.current = true;

        if (result.audio_url) {
          // Play MagpieTTS audio from NVIDIA endpoint
          console.log('[Brainstorm] Playing MagpieTTS audio: %s', result.audio_url);
          await new Promise<void>((resolve) => {
            const audio = new Audio(result.audio_url);
            audioRef.current = audio;
            audio.onended = () => {
              audioRef.current = null;
              resolve();
            };
            audio.onerror = () => {
              console.warn('[Brainstorm] MagpieTTS audio playback failed, falling back to browser TTS');
              audioRef.current = null;
              // Fallback to browser SpeechSynthesis
              const utterance = new SpeechSynthesisUtterance(result.reply);
              utterance.onend = () => resolve();
              utterance.onerror = () => resolve();
              speechSynthesis.speak(utterance);
            };
            audio.play().catch(() => {
              audioRef.current = null;
              console.warn('[Brainstorm] MagpieTTS audio.play() failed, using browser TTS');
              const utterance = new SpeechSynthesisUtterance(result.reply);
              utterance.onend = () => resolve();
              utterance.onerror = () => resolve();
              speechSynthesis.speak(utterance);
            });
          });
        } else {
          // No MagpieTTS URL — fall back to browser SpeechSynthesis
          console.log('[Brainstorm] No MagpieTTS audio, using browser TTS');
          await new Promise<void>((resolve) => {
            const utterance = new SpeechSynthesisUtterance(result.reply);
            utterance.onend = () => resolve();
            utterance.onerror = () => resolve();
            speechSynthesis.speak(utterance);
          });
        }

        aiSpeakingRef.current = false;
        console.log('[Brainstorm] TTS finished');

        // After TTS finishes, return to listening (if not interrupted/stopped)
        if (loopStateRef.current === 'ai_speaking') {
          dispatch({ type: 'SET_STATE', state: 'listening' });
        }
      }
    } catch (err) {
      const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
      console.error('[Brainstorm] AI turn failed after %ss:', elapsed, err);
      if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        console.error('[Brainstorm] Network error — backend may be down or unreachable');
      }

      const errorReply = "I lost my train of thought — could you say that again?";
      dispatch({ type: 'AI_REPLY', reply: errorReply });
      dispatch({
        type: 'ADD_TURN',
        entry: { role: 'ai', content: errorReply, timestamp: Date.now() },
      });

      // Return to listening on error
      if (loopStateRef.current !== 'idle') {
        dispatch({ type: 'SET_STATE', state: 'listening' });
      }
    }
  }, [cards, transcript, voice.transcript, appendCards, updateCard]);

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  const startBrainstorm = useCallback(async () => {
    console.log('[Brainstorm] Starting brainstorm session');
    dispatch({ type: 'START' });
    lastTriggerOffsetRef.current = voice.transcript.length;
    await voice.start();
    console.log('[Brainstorm] Mic started, listening for speech');
  }, [voice]);

  const stopBrainstorm = useCallback(() => {
    console.log('[Brainstorm] Stopping brainstorm session, history=%d turns', conversationRef.current.length);
    if (pauseTimerRef.current) {
      clearTimeout(pauseTimerRef.current);
      pauseTimerRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    speechSynthesis.cancel();
    aiSpeakingRef.current = false;
    voice.stop();
    dispatch({ type: 'STOP' });
  }, [voice]);

  const triggerAiTurn = useCallback(() => {
    const currentText = voice.transcript.slice(lastTriggerOffsetRef.current).trim();
    console.log('[Brainstorm] Manual trigger: "%s"', currentText.slice(0, 80));
    if (currentText) {
      fireAiTurn(currentText);
    } else {
      console.log('[Brainstorm] Manual trigger skipped — no new speech since last turn');
    }
  }, [voice.transcript, fireAiTurn]);

  const interruptAi = useCallback(() => {
    console.log('[Brainstorm] User interrupted AI speaking');
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    speechSynthesis.cancel();
    aiSpeakingRef.current = false;
    dispatch({ type: 'SET_STATE', state: 'listening' });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pauseTimerRef.current) {
        clearTimeout(pauseTimerRef.current);
      }
    };
  }, []);

  return {
    loopState: state.loopState,
    isActive: state.loopState !== 'idle',
    conversationHistory: state.conversationHistory,
    currentUtterance: state.currentUtterance,
    aiResponse: state.aiResponse,
    startBrainstorm,
    stopBrainstorm,
    triggerAiTurn,
    interruptAi,
  };
}
