import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';

type PlaybackState = 'idle' | 'loading' | 'playing' | 'paused';

/**
 * Hook for text-to-speech functionality.
 *
 * Tries MagpieTTS backend first for high-quality audio,
 * falls back to browser SpeechSynthesis API if unavailable.
 */
export function useReadAloud() {
  const [state, setState] = useState<PlaybackState>('idle');
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const startTimeRef = useRef<number>(0);
  const pauseTimeRef = useRef<number>(0);

  const { ttsSpeed, voiceEnabled } = useSettingsStore();

  // Initialize AudioContext
  useEffect(() => {
    audioContextRef.current = new AudioContext();
    return () => {
      audioContextRef.current?.close();
    };
  }, []);

  /**
   * Try to play using MagpieTTS backend (high quality)
   */
  const playWithMagpieTTS = useCallback(async (
    text: string,
    voice: string = 'default'
  ): Promise<boolean> => {
    try {
      setState('loading');
      const response = await api.textToSpeech(text, voice);
      const audioUrl = response.data.audio_url;

      // Fetch audio file
      const audioResponse = await fetch(audioUrl);
      const arrayBuffer = await audioResponse.arrayBuffer();

      // Decode to audio buffer
      const ctx = audioContextRef.current!;
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      // Create source
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.playbackRate.value = ttsSpeed;
      source.connect(ctx.destination);

      // Handle end
      source.onended = () => {
        setState('idle');
        sourceNodeRef.current = null;
      };

      // Play
      source.start(0);
      sourceNodeRef.current = source;
      startTimeRef.current = ctx.currentTime;
      setState('playing');

      return true;
    } catch (err) {
      console.warn('[TTS] MagpieTTS failed, falling back to browser TTS:', err);
      return false;
    }
  }, [ttsSpeed]);

  /**
   * Fallback to browser SpeechSynthesis API
   */
  const playWithBrowserTTS = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) {
      setError('Text-to-speech not supported in this browser');
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = ttsSpeed;
    utterance.onstart = () => setState('playing');
    utterance.onend = () => setState('idle');
    utterance.onerror = (e) => setError(e.error);

    speechSynthesis.speak(utterance);
  }, [ttsSpeed]);

  /**
   * Speak the given text
   */
  const speak = useCallback(async (text: string, voice?: string) => {
    if (!voiceEnabled) {
      console.log('[TTS] Voice disabled in settings');
      return;
    }

    setError(null);

    // Try MagpieTTS first
    const success = await playWithMagpieTTS(text, voice);

    // Fallback to browser
    if (!success) {
      playWithBrowserTTS(text);
    }
  }, [voiceEnabled, playWithMagpieTTS, playWithBrowserTTS]);

  /**
   * Pause playback
   */
  const pause = useCallback(() => {
    if (state === 'playing') {
      const source = sourceNodeRef.current;
      if (source) {
        // MagpieTTS: stop source node
        pauseTimeRef.current = audioContextRef.current!.currentTime - startTimeRef.current;
        source.stop();
        sourceNodeRef.current = null;
        setState('paused');
      } else {
        // Browser TTS
        speechSynthesis.pause();
        setState('paused');
      }
    }
  }, [state]);

  /**
   * Resume playback
   */
  const resume = useCallback(() => {
    if (state === 'paused') {
      // Browser TTS resume
      if (speechSynthesis.paused) {
        speechSynthesis.resume();
        setState('playing');
      }
      // Note: MagpieTTS resume would require re-creating source at offset
      // For now, user can replay from beginning
    }
  }, [state]);

  /**
   * Stop playback
   */
  const stop = useCallback(() => {
    const source = sourceNodeRef.current;
    if (source) {
      source.stop();
      sourceNodeRef.current = null;
    }
    speechSynthesis.cancel();
    setState('idle');
    pauseTimeRef.current = 0;
  }, []);

  return {
    speak,
    pause,
    resume,
    stop,
    state,
    error,
    isPlaying: state === 'playing',
    isPaused: state === 'paused',
    isLoading: state === 'loading',
  };
}
