/**
 * Composition hook for Capture Mode voice input.
 *
 * Primary path: Web Speech API (real-time browser transcription) + AudioContext for waveform.
 * Fallback path: MediaRecorder + backend /capture/transcribe (for browsers without Speech API).
 *
 * In both paths a background MediaRecorder runs on the same stream to capture
 * audio blobs for playback.
 */

import { useState, useRef, useCallback } from 'react';
import { useVoiceInput } from './useVoiceInput';
import { useMediaRecorder } from './useMediaRecorder';
import { useMicPermission } from './useMicPermission';
import { api } from '../services/api';

interface UseCaptureVoiceReturn {
  isRecording: boolean;
  transcript: string;
  interimText: string;
  analyserNode: AnalyserNode | null;
  isSupported: boolean;
  /** True when fallback path is transcribing after stop */
  isTranscribing: boolean;
  /** True when microphone access is denied in browser */
  micDenied: boolean;
  /** Last recorded audio blob (available after stop) */
  lastBlob: Blob | null;
  start: () => Promise<void>;
  stop: () => Promise<string>;
  resetTranscript: () => void;
}

/**
 * Returns the best supported MIME type for background MediaRecorder.
 */
function getBgMimeType(): string {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
  ];
  for (const t of types) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t)) return t;
  }
  return '';
}

export function useCaptureVoice(): UseCaptureVoiceReturn {
  const voice = useVoiceInput({ continuous: true });
  const recorder = useMediaRecorder();
  const { isDenied, checkPermission, recordGranted, recordDenied } = useMicPermission();

  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const [fallbackTranscript, setFallbackTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [lastBlob, setLastBlob] = useState<Blob | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const bgRecorderRef = useRef<MediaRecorder | null>(null);
  const bgChunksRef = useRef<Blob[]>([]);
  const usingWebSpeech = voice.isSupported;

  const start = useCallback(async () => {
    // Check mic permission before attempting getUserMedia
    const permState = await checkPermission();

    if (permState === 'denied') {
      // Don't attempt getUserMedia — it will fail.
      // Text entry is still available via the textarea.
      return;
    }

    // Open mic for waveform visualisation (both paths need this)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      recordGranted();

      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioContextRef.current = ctx;
      setAnalyserNode(analyser);

      // Start background MediaRecorder for blob capture
      try {
        const mimeType = getBgMimeType();
        const bgRec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        bgChunksRef.current = [];
        bgRec.ondataavailable = (e) => {
          if (e.data.size > 0) bgChunksRef.current.push(e.data);
        };
        bgRec.start();
        bgRecorderRef.current = bgRec;
      } catch {
        // Background recorder is non-critical — continue without it
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        recordDenied();
        return;
      }
      // Other error — still allow text entry, just no waveform
    }

    if (usingWebSpeech) {
      voice.resetTranscript();
      voice.startListening();
    } else {
      setFallbackTranscript('');
      await recorder.startRecording();
    }
  }, [usingWebSpeech, voice, recorder, checkPermission, recordGranted, recordDenied]);

  const stop = useCallback(async (): Promise<string> => {
    // Collect background recorder blob
    const bgRec = bgRecorderRef.current;
    if (bgRec && bgRec.state !== 'inactive') {
      await new Promise<void>((resolve) => {
        bgRec.onstop = () => {
          const blob = new Blob(bgChunksRef.current, { type: bgRec.mimeType });
          setLastBlob(blob);
          bgChunksRef.current = [];
          resolve();
        };
        bgRec.stop();
      });
    }
    bgRecorderRef.current = null;

    // Tear down audio context / stream
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    setAnalyserNode(null);

    if (usingWebSpeech) {
      voice.stopListening();
      return voice.transcript;
    }

    // Fallback: stop recorder, send blob to backend
    const blob = await recorder.stopRecording();
    if (!blob) return '';

    setIsTranscribing(true);
    try {
      const result = await api.transcribeAudio(blob);
      setFallbackTranscript(result.transcript);
      return result.transcript;
    } catch {
      return '';
    } finally {
      setIsTranscribing(false);
    }
  }, [usingWebSpeech, voice, recorder]);

  const resetTranscript = useCallback(() => {
    voice.resetTranscript();
    setFallbackTranscript('');
  }, [voice]);

  return {
    isRecording: usingWebSpeech ? voice.isListening : recorder.isRecording,
    transcript: usingWebSpeech ? voice.transcript : fallbackTranscript,
    interimText: usingWebSpeech ? voice.interimText : '',
    analyserNode,
    isSupported: true, // Always supported — fallback uses MediaRecorder
    isTranscribing,
    micDenied: isDenied,
    lastBlob,
    start,
    stop,
    resetTranscript,
  };
}
