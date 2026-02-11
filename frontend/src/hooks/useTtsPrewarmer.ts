import { useEffect, useRef, useCallback } from 'react';
import { Editor } from '@tiptap/react';
import { api } from '@/services/api';
import {
  splitIntoSentences,
  findUncachedSentences,
  sentenceAudioCache,
} from '@/services/ttsSentenceCache';

const IDLE_MS = 2000;
const DEBOUNCE_MS = 3000;
const MAX_BATCH = 20;

/**
 * Pre-warms the TTS sentence cache by generating audio for changed
 * sentences while the user is idle. Only activates after the user
 * has clicked "Read Aloud" at least once (detected via the
 * `dyslex-tts-used` custom event or existing cache entries).
 */
export function useTtsPrewarmer(editor: Editor | null) {
  const activeRef = useRef(false);
  const lastEditRef = useRef<number>(0);
  const lastApiCallRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Activate once TTS has been used
  const activate = useCallback(() => {
    activeRef.current = true;
  }, []);

  useEffect(() => {
    // If cache already has entries, TTS was used before this mount
    if (sentenceAudioCache.size > 0) {
      activeRef.current = true;
    }

    document.addEventListener('dyslex-tts-used', activate);
    return () => {
      document.removeEventListener('dyslex-tts-used', activate);
    };
  }, [activate]);

  // Core pre-warm logic
  const prewarm = useCallback(async () => {
    if (!editor || !activeRef.current) return;

    const now = Date.now();
    if (now - lastApiCallRef.current < DEBOUNCE_MS) return;

    const text = editor.getText();
    if (!text || text.trim().length < 5) return;

    const sentences = splitIntoSentences(text);
    if (sentences.length === 0) return;

    const uncached = await findUncachedSentences(
      sentences,
      'default',
      sentenceAudioCache,
    );

    if (uncached.length === 0) return;

    // Cancel any previous in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const abortController = new AbortController();
    abortRef.current = abortController;
    lastApiCallRef.current = Date.now();

    const batch = uncached.slice(0, MAX_BATCH);
    console.log(`[TTS Prewarm] Warming ${batch.length} sentences`);

    try {
      const response = await api.textToSpeechBatch(
        batch.map(s => ({ index: s.index, text: s.text })),
        'default',
        abortController.signal,
      );

      if (abortController.signal.aborted) return;

      // Lazily create AudioContext for decoding
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;

      const results = response.data.results;
      await Promise.all(
        results
          .filter(r => r.audio_url)
          .map(async (r) => {
            const match = batch.find(b => b.index === r.index);
            if (!match) return;
            const audioResp = await fetch(r.audio_url, {
              signal: abortController.signal,
            });
            const arrayBuf = await audioResp.arrayBuffer();
            const audioBuffer = await ctx.decodeAudioData(arrayBuf);
            sentenceAudioCache.set(match.hash, audioBuffer);
          }),
      );
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.warn('[TTS Prewarm] Failed:', err);
      }
    } finally {
      if (abortRef.current === abortController) {
        abortRef.current = null;
      }
    }
  }, [editor]);

  // Listen to editor updates for idle detection
  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => {
      lastEditRef.current = Date.now();

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      timerRef.current = setTimeout(() => {
        // Only fire if still idle (no edits since timer was set)
        if (Date.now() - lastEditRef.current >= IDLE_MS - 100) {
          prewarm();
        }
      }, IDLE_MS);
    };

    editor.on('update', handleUpdate);

    return () => {
      editor.off('update', handleUpdate);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, [editor, prewarm]);

  // Cleanup AudioContext on unmount
  useEffect(() => {
    return () => {
      audioCtxRef.current?.close();
      audioCtxRef.current = null;
    };
  }, []);
}
