/**
 * Composition hook for Capture Mode voice input.
 *
 * Primary path: Web Speech API (real-time browser transcription) + AudioContext for waveform.
 * Fallback path: MediaRecorder + backend /capture/transcribe (for browsers without Speech API).
 */

import { useState, useRef, useCallback } from 'react';
import { useVoiceInput } from './useVoiceInput';
import { useMediaRecorder } from './useMediaRecorder';
import { api } from '../services/api';

interface UseCaptureVoiceReturn {
  isRecording: boolean;
  transcript: string;
  interimText: string;
  analyserNode: AnalyserNode | null;
  isSupported: boolean;
  /** True when fallback path is transcribing after stop */
  isTranscribing: boolean;
  start: () => Promise<void>;
  stop: () => Promise<string>;
  resetTranscript: () => void;
}

export function useCaptureVoice(): UseCaptureVoiceReturn {
  const voice = useVoiceInput({ continuous: true });
  const recorder = useMediaRecorder();

  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);
  const [fallbackTranscript, setFallbackTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const usingWebSpeech = voice.isSupported;

  const start = useCallback(async () => {
    // Open mic for waveform visualisation (both paths need this)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ctx = new AudioContext();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioContextRef.current = ctx;
      setAnalyserNode(analyser);
    } catch {
      // Mic access denied — still allow text entry, just no waveform
    }

    if (usingWebSpeech) {
      voice.resetTranscript();
      voice.startListening();
    } else {
      setFallbackTranscript('');
      await recorder.startRecording();
    }
  }, [usingWebSpeech, voice, recorder]);

  const stop = useCallback(async (): Promise<string> => {
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
    start,
    stop,
    resetTranscript,
  };
}
