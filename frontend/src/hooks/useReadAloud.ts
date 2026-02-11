import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '@/services/api';
import { useSettingsStore } from '@/stores/settingsStore';
import {
  splitIntoSentences,
  hashSentence,
  sentenceAudioCache,
} from '@/services/ttsSentenceCache';

type PlaybackState = 'idle' | 'loading' | 'playing' | 'paused';

const BATCH_SIZE = 50;
const SILENCE_GAP_MS = 150;

/**
 * Concatenate multiple AudioBuffers into one with silence gaps between them.
 */
function concatenateAudioBuffers(
  buffers: AudioBuffer[],
  ctx: AudioContext,
  gapMs: number = SILENCE_GAP_MS,
): AudioBuffer {
  if (buffers.length === 0) {
    return ctx.createBuffer(1, 1, ctx.sampleRate);
  }
  if (buffers.length === 1) return buffers[0];

  const sampleRate = buffers[0].sampleRate;
  const channels = buffers[0].numberOfChannels;
  const gapSamples = Math.round((gapMs / 1000) * sampleRate);

  let totalLength = 0;
  for (const buf of buffers) {
    totalLength += buf.length;
  }
  // Add gaps between sentences (not after last)
  totalLength += gapSamples * (buffers.length - 1);

  const output = ctx.createBuffer(channels, totalLength, sampleRate);

  for (let ch = 0; ch < channels; ch++) {
    const outData = output.getChannelData(ch);
    let offset = 0;

    for (let i = 0; i < buffers.length; i++) {
      const srcChannels = buffers[i].numberOfChannels;
      // If source doesn't have this channel, fill with silence
      if (ch < srcChannels) {
        outData.set(buffers[i].getChannelData(ch), offset);
      }
      offset += buffers[i].length;

      // Insert silence gap (except after last buffer)
      if (i < buffers.length - 1) {
        // outData is already zeroed by createBuffer
        offset += gapSamples;
      }
    }
  }

  return output;
}

/**
 * Hook for text-to-speech functionality.
 *
 * Tries MagpieTTS backend first for high-quality audio,
 * falls back to browser SpeechSynthesis API if unavailable.
 *
 * Uses sentence-level splitting and caching so that re-reading
 * a document after minor edits only synthesizes changed sentences.
 */
export function useReadAloud() {
  const [state, setState] = useState<PlaybackState>('idle');
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const startTimeRef = useRef<number>(0);
  const pauseTimeRef = useRef<number>(0);
  const abortRef = useRef<AbortController | null>(null);

  const { ttsSpeed, voiceEnabled } = useSettingsStore();

  // Initialize AudioContext
  useEffect(() => {
    audioContextRef.current = new AudioContext();
    return () => {
      audioContextRef.current?.close();
    };
  }, []);

  /**
   * Try to play using MagpieTTS backend with sentence batching & caching.
   */
  const playWithMagpieTTS = useCallback(async (
    text: string,
    voice: string = 'default',
  ): Promise<boolean> => {
    try {
      setState('loading');

      const ctx = audioContextRef.current!;
      if (ctx.state === 'suspended') await ctx.resume();

      const sentences = splitIntoSentences(text);
      if (sentences.length === 0) {
        setState('idle');
        return true;
      }

      // Hash every sentence
      const hashes = await Promise.all(
        sentences.map(s => hashSentence(s, voice)),
      );

      // Partition into cached / uncached
      const cached: Map<number, AudioBuffer> = new Map();
      const uncached: Array<{ index: number; text: string }> = [];

      for (let i = 0; i < sentences.length; i++) {
        const buf = sentenceAudioCache.get(hashes[i]);
        if (buf) {
          cached.set(i, buf);
        } else {
          uncached.push({ index: i, text: sentences[i] });
        }
      }

      // Fetch uncached sentences via batch endpoint (chunked at BATCH_SIZE)
      if (uncached.length > 0) {
        const abortController = new AbortController();
        abortRef.current = abortController;

        for (let start = 0; start < uncached.length; start += BATCH_SIZE) {
          if (abortController.signal.aborted) return false;

          const chunk = uncached.slice(start, start + BATCH_SIZE);
          const response = await api.textToSpeechBatch(chunk, voice, abortController.signal);
          const results = response.data.results;

          // Fetch each audio URL, decode, and cache
          const fetches = results
            .filter(r => r.audio_url)
            .map(async (r) => {
              const audioResp = await fetch(r.audio_url, { signal: abortController.signal });
              const arrayBuf = await audioResp.arrayBuffer();
              const audioBuffer = await ctx.decodeAudioData(arrayBuf);
              sentenceAudioCache.set(hashes[r.index], audioBuffer);
              cached.set(r.index, audioBuffer);
            });

          await Promise.all(fetches);
        }

        abortRef.current = null;
      }

      // Assemble all buffers in sentence order
      const orderedBuffers: AudioBuffer[] = [];
      for (let i = 0; i < sentences.length; i++) {
        const buf = cached.get(i);
        if (buf) orderedBuffers.push(buf);
      }

      if (orderedBuffers.length === 0) return false;

      const combined = concatenateAudioBuffers(orderedBuffers, ctx);

      // Create source and play
      const source = ctx.createBufferSource();
      source.buffer = combined;
      source.playbackRate.value = ttsSpeed;
      source.connect(ctx.destination);

      source.onended = () => {
        setState('idle');
        sourceNodeRef.current = null;
      };

      source.start(0);
      sourceNodeRef.current = source;
      startTimeRef.current = ctx.currentTime;
      setState('playing');

      return true;
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        setState('idle');
        return true; // User intentionally stopped
      }
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

    // Signal to pre-warmer that TTS is active this session
    document.dispatchEvent(new Event('dyslex-tts-used'));

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
    // Cancel any in-flight fetch requests
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

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
