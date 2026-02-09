/**
 * Hook that triggers incremental idea extraction while the user is recording.
 *
 * Monitors the transcript for new content (50+ new words since last extraction)
 * and triggers extraction after a 2-second speech pause. Also runs a periodic
 * check every 30 seconds during long recordings.
 *
 * Extracted cards are appended (not replaced) with title-based deduplication.
 */

import { useEffect, useRef } from 'react';
import { useCaptureStore } from '../stores/captureStore';
import { api } from '../services/api';

const MIN_NEW_WORDS = 50;
const PAUSE_TIMEOUT_MS = 2000;
const PERIODIC_INTERVAL_MS = 30000;

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function useIncrementalExtraction(
  isRecording: boolean,
  transcript: string,
): void {
  const setLastExtractedOffset = useCaptureStore((s) => s.setLastExtractedOffset);
  const setIncrementalExtracting = useCaptureStore((s) => s.setIncrementalExtracting);
  const appendCards = useCaptureStore((s) => s.appendCards);

  const pauseTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const periodicTimerRef = useRef<ReturnType<typeof setInterval>>();
  const prevTranscriptLenRef = useRef(0);

  // Core extraction function
  const tryExtract = useRef(async () => {
    const currentTranscript = useCaptureStore.getState().transcript;
    const offset = useCaptureStore.getState().lastExtractedOffset;
    const newText = currentTranscript.slice(offset);

    if (wordCount(newText) < MIN_NEW_WORDS) return;
    if (useCaptureStore.getState().isIncrementalExtracting) return;

    const existingTitles = useCaptureStore.getState().cards.map((c) => c.title);

    setIncrementalExtracting(true);
    try {
      const result = await api.extractIdeas(currentTranscript, existingTitles);
      const normalized = result.cards.map((c) => ({
        ...c,
        sub_ideas: c.sub_ideas || [],
      }));
      appendCards(normalized);
      setLastExtractedOffset(currentTranscript.length);
    } catch {
      // Non-blocking — don't show error for incremental extraction
    } finally {
      setIncrementalExtracting(false);
    }
  });

  // Update the ref closure when dependencies change
  useEffect(() => {
    tryExtract.current = async () => {
      const currentTranscript = useCaptureStore.getState().transcript;
      const offset = useCaptureStore.getState().lastExtractedOffset;
      const newText = currentTranscript.slice(offset);

      if (wordCount(newText) < MIN_NEW_WORDS) return;
      if (useCaptureStore.getState().isIncrementalExtracting) return;

      const existingTitles = useCaptureStore.getState().cards.map((c) => c.title);

      setIncrementalExtracting(true);
      try {
        const result = await api.extractIdeas(currentTranscript, existingTitles);
        const normalized = result.cards.map((c) => ({
          ...c,
          sub_ideas: c.sub_ideas || [],
        }));
        appendCards(normalized);
        setLastExtractedOffset(currentTranscript.length);
      } catch {
        // Non-blocking
      } finally {
        setIncrementalExtracting(false);
      }
    };
  }, [appendCards, setLastExtractedOffset, setIncrementalExtracting]);

  // Detect speech pauses — when transcript stops changing for 2s
  useEffect(() => {
    if (!isRecording) return;

    const currentLen = transcript.length;
    if (currentLen === prevTranscriptLenRef.current) return;
    prevTranscriptLenRef.current = currentLen;

    // Reset pause timer on new speech
    clearTimeout(pauseTimerRef.current);
    pauseTimerRef.current = setTimeout(() => {
      tryExtract.current();
    }, PAUSE_TIMEOUT_MS);

    return () => clearTimeout(pauseTimerRef.current);
  }, [isRecording, transcript]);

  // Periodic extraction every 30s during recording
  useEffect(() => {
    if (!isRecording) {
      clearInterval(periodicTimerRef.current);
      return;
    }

    periodicTimerRef.current = setInterval(() => {
      tryExtract.current();
    }, PERIODIC_INTERVAL_MS);

    return () => clearInterval(periodicTimerRef.current);
  }, [isRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(pauseTimerRef.current);
      clearInterval(periodicTimerRef.current);
    };
  }, []);
}
