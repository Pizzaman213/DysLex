/**
 * WebSocket client hook for real-time streaming transcription.
 */

import { useRef, useState, useCallback } from 'react';

interface StreamingMessage {
  type: 'partial' | 'final' | 'error' | 'ready';
  text?: string;
  message?: string;
  timestamp?: number;
}

export function useStreamingTranscription() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const startStreaming = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const ws = new WebSocket('ws://localhost:8000/api/v1/voice/stream');
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'start',
          sampleRate: 48000,
          mimeType: 'audio/webm;codecs=opus'
        }));
      };

      ws.onmessage = (event) => {
        const data: StreamingMessage = JSON.parse(event.data);

        if (data.type === 'ready') {
          startRecording(stream, ws);
        } else if (data.type === 'partial') {
          setTranscript(data.text || '');
        } else if (data.type === 'final') {
          setTranscript(data.text || '');
          setIsStreaming(false);
        } else if (data.type === 'error') {
          setError(data.message || 'Streaming error');
          setIsStreaming(false);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection failed');
        setIsStreaming(false);
      };

      setIsStreaming(true);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start');
    }
  }, []);

  const startRecording = (stream: MediaStream, ws: WebSocket) => {
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus'
    });
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
        event.data.arrayBuffer().then(buffer => {
          ws.send(buffer);
        });
      }
    };

    mediaRecorder.start(250); // 250ms chunks
  };

  const stopStreaming = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'stop' }));
    }

    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());

    wsRef.current?.close();
    wsRef.current = null;
    mediaRecorderRef.current = null;
  }, []);

  return {
    isStreaming,
    transcript,
    error,
    startStreaming,
    stopStreaming
  };
}
