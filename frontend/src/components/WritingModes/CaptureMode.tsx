/**
 * Capture Mode — Voice-to-Thought recording, transcription, and idea extraction.
 * Centered hero layout with big mic, waveform, transcript area, and thought cards.
 */

import { useEffect, useRef } from 'react';
import { useCaptureStore } from '../../stores/captureStore';
import { useCaptureVoice } from '../../hooks/useCaptureVoice';
import { useReadAloud } from '../../hooks/useReadAloud';
import { api } from '../../services/api';
import { VoiceBar } from '../Shared/VoiceBar';
import { StatusBar } from '../Shared/StatusBar';
import { ThoughtCardGrid } from './ThoughtCardGrid';

interface CaptureModeProps {
  onNavigateToMindMap?: () => void;
}

export function CaptureMode({ onNavigateToMindMap }: CaptureModeProps) {
  const phase = useCaptureStore((s) => s.phase);
  const transcript = useCaptureStore((s) => s.transcript);
  const cards = useCaptureStore((s) => s.cards);
  const error = useCaptureStore((s) => s.error);
  const setPhase = useCaptureStore((s) => s.setPhase);
  const setTranscript = useCaptureStore((s) => s.setTranscript);
  const setCards = useCaptureStore((s) => s.setCards);
  const setError = useCaptureStore((s) => s.setError);

  const voice = useCaptureVoice();
  const micDenied = voice.micDenied;
  const { speak, stop: stopReadAloud, isPlaying, isLoading } = useReadAloud();
  const prevTranscriptRef = useRef(voice.transcript);

  // Sync live voice transcript into the store while recording
  useEffect(() => {
    if (voice.isRecording && voice.transcript !== prevTranscriptRef.current) {
      prevTranscriptRef.current = voice.transcript;
      setTranscript(voice.transcript);
    }
  }, [voice.isRecording, voice.transcript, setTranscript]);

  const handleStartRecording = async () => {
    setError(null);
    setPhase('recording');
    await voice.start();
  };

  const handleStopRecording = async () => {
    const finalTranscript = await voice.stop();

    // Fallback path may briefly show "transcribing" spinner
    if (voice.isTranscribing) {
      setPhase('transcribing');
    }

    setTranscript(finalTranscript);

    if (finalTranscript.trim()) {
      await handleExtractIdeas(finalTranscript);
    } else {
      setError('No speech detected in recording');
      setPhase('idle');
    }
  };

  const handleExtractIdeas = async (textToAnalyze?: string) => {
    const text = textToAnalyze || transcript;

    if (!text.trim()) {
      setError('No transcript to analyze');
      return;
    }

    setPhase('extracting');
    setError(null);

    try {
      const result = await api.extractIdeas(text);
      setCards(result.cards);
      setPhase('review');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Idea extraction failed';
      setError(message);
      setPhase('idle');
    }
  };

  const handleReadBack = async () => {
    if (isPlaying || isLoading) {
      stopReadAloud();
    } else {
      await speak(transcript);
    }
  };

  const handleContinueToMindMap = () => {
    if (onNavigateToMindMap) {
      onNavigateToMindMap();
    }
  };

  const showThoughtCards = phase === 'extracting' || phase === 'review';
  const canContinue = phase === 'review' && cards.length > 0;
  const isRecording = voice.isRecording;

  return (
    <div className="capture-mode">
      <div className="capture-area anim">
        <div className="capture-hero anim anim-d1">
          <h2>Capture Your Ideas</h2>
          <p>Type or tap the microphone and talk freely. We'll organize your thoughts into cards you can rearrange.</p>
        </div>

        <button
          className={`big-mic ${isRecording ? 'recording' : ''}`}
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          disabled={phase === 'transcribing' || phase === 'extracting'}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
          aria-pressed={isRecording}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </button>

        <div className={`big-wave ${isRecording ? 'active' : ''}`} aria-hidden="true">
          <span /><span /><span /><span /><span /><span /><span />
        </div>

        {micDenied && (
          <div className="capture-mic-hint" role="status">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
            <p>Microphone access is blocked. To re-enable, click the lock icon in your browser's address bar and allow microphone access, then reload the page.</p>
          </div>
        )}

        {isRecording && (
          <span className="vstatus anim">Listening...</span>
        )}

        {phase === 'transcribing' && (
          <div className="voice-indicator" aria-live="polite">
            <div className="capture-spinner" aria-hidden="true" />
            <span>Transcribing...</span>
          </div>
        )}

        {phase === 'extracting' && (
          <div className="voice-indicator" aria-live="polite">
            <div className="capture-spinner" aria-hidden="true" />
            <span>Extracting ideas...</span>
          </div>
        )}

        {error && (
          <div className="capture-error anim" role="alert">
            <span className="capture-error-icon" aria-hidden="true">!</span>
            <p>{error}</p>
          </div>
        )}

        <div className={`capture-transcript ${transcript ? 'has-text' : ''}`}>
          <textarea
            className="transcript-textarea"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Type or speak your ideas here..."
            aria-label="Voice transcript"
            spellCheck={false}
          />
        </div>

        {showThoughtCards && cards.length > 0 && (
          <span className="tc-label anim">
            AI identified {cards.length} idea cluster{cards.length !== 1 ? 's' : ''}
          </span>
        )}

        {showThoughtCards && (
          <div className="thought-cards anim anim-d2">
            <ThoughtCardGrid isLoading={phase === 'extracting'} />
          </div>
        )}

        {phase === 'review' && transcript && (
          <button
            className="btn btn-secondary"
            onClick={() => handleExtractIdeas()}
            disabled={!transcript.trim()}
          >
            Re-analyze Ideas
          </button>
        )}

        {canContinue && (
          <button
            className="btn btn-primary anim anim-d3"
            onClick={handleContinueToMindMap}
            aria-label="Continue to Mind Map mode"
          >
            Continue to Mind Map
          </button>
        )}

        <div className="capture-tip anim anim-d4">
          Tip: Speak in complete thoughts. Pause between ideas for better organization.
        </div>
      </div>

      {transcript.trim() && (
        <button
          className="capture-speak-btn"
          onClick={handleReadBack}
          aria-label={isLoading ? 'Loading audio' : isPlaying ? 'Stop reading' : 'Read back transcript'}
        >
          {isLoading ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="capture-speak-spinner">
              <circle cx="12" cy="12" r="10" />
            </svg>
          ) : isPlaying ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <rect x="6" y="5" width="4" height="14" rx="1" />
              <rect x="14" y="5" width="4" height="14" rx="1" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
          )}
        </button>
      )}

      <VoiceBar
        isRecording={isRecording}
        isTranscribing={phase === 'transcribing'}
        analyserNode={voice.analyserNode}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
        micDenied={micDenied}
        compact
      />
      <StatusBar />
    </div>
  );
}
