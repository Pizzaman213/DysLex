/**
 * Capture Mode — Voice-to-Thought recording, transcription, and idea extraction.
 * Centered hero layout with big mic, waveform, transcript area, and thought cards.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useCaptureStore } from '../../stores/captureStore';
import { useCaptureVoice } from '../../hooks/useCaptureVoice';
import { useRadialWaveform } from '../../hooks/useRadialWaveform';
import { useIncrementalExtraction } from '../../hooks/useIncrementalExtraction';
import { useReadAloud } from '../../hooks/useReadAloud';
import { useBrainstormLoop } from '../../hooks/useBrainstormLoop';
import { api } from '../../services/api';
import { mergeCards } from '../../utils/mergeCards';
import { ThoughtCardGrid } from './ThoughtCardGrid';
import { BrainstormPanel } from './BrainstormPanel';
import { VisionCapturePanel } from '../Shared/VisionCapturePanel';

interface CaptureModeProps {
  onNavigateToMindMap?: () => void;
}

export function CaptureMode({ onNavigateToMindMap }: CaptureModeProps) {
  const phase = useCaptureStore((s) => s.phase);
  const transcript = useCaptureStore((s) => s.transcript);
  const cards = useCaptureStore((s) => s.cards);
  const error = useCaptureStore((s) => s.error);
  const takes = useCaptureStore((s) => s.takes);
  const audioUrls = useCaptureStore((s) => s.audioUrls);
  const setPhase = useCaptureStore((s) => s.setPhase);
  const setTranscript = useCaptureStore((s) => s.setTranscript);
  const appendTranscript = useCaptureStore((s) => s.appendTranscript);
  const setCards = useCaptureStore((s) => s.setCards);
  const setError = useCaptureStore((s) => s.setError);
  const incrementTakes = useCaptureStore((s) => s.incrementTakes);
  const addAudioBlob = useCaptureStore((s) => s.addAudioBlob);

  const brainstormAutoProbe = useCaptureStore((s) => s.brainstormAutoProbe);
  const setBrainstormActive = useCaptureStore((s) => s.setBrainstormActive);
  const setBrainstormAutoProbe = useCaptureStore((s) => s.setBrainstormAutoProbe);

  const showVisionCapture = useCaptureStore((s) => s.showVisionCapture);
  const isVisionProcessing = useCaptureStore((s) => s.isVisionProcessing);
  const setShowVisionCapture = useCaptureStore((s) => s.setShowVisionCapture);
  const setIsVisionProcessing = useCaptureStore((s) => s.setIsVisionProcessing);
  const appendCards = useCaptureStore((s) => s.appendCards);

  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const playingAudioRef = useRef<HTMLAudioElement | null>(null);

  // Delayed-unmount for smooth pill close animation
  const [visionMounted, setVisionMounted] = useState(false);
  const visionCloseTimer = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    if (showVisionCapture) {
      if (visionCloseTimer.current) clearTimeout(visionCloseTimer.current);
      setVisionMounted(true);
    } else if (visionMounted) {
      // Keep content mounted until all closing transitions finish (max: 0.4s + 0.12s delay)
      visionCloseTimer.current = setTimeout(() => setVisionMounted(false), 600);
    }
    return () => { if (visionCloseTimer.current) clearTimeout(visionCloseTimer.current); };
  }, [showVisionCapture]);

  const handleVisionClose = useCallback(() => {
    setShowVisionCapture(false);
  }, [setShowVisionCapture]);

  const voice = useCaptureVoice();
  const micDenied = voice.micDenied;
  const radialWaveRef = useRef<HTMLDivElement>(null);
  useRadialWaveform(radialWaveRef, voice.analyserNode);
  const { speak, stop: stopReadAloud, isPlaying, isLoading } = useReadAloud();
  const brainstorm = useBrainstormLoop(voice);
  const prevTranscriptRef = useRef(voice.transcript);
  // Snapshot of the store transcript when a new take starts, so we can
  // show "base + live voice" without overwriting previous takes.
  const baseTranscriptRef = useRef('');

  // Incremental extraction during recording
  useIncrementalExtraction(voice.isRecording, transcript);

  // Sync live voice transcript into the store while recording
  useEffect(() => {
    if (voice.isRecording && voice.transcript !== prevTranscriptRef.current) {
      prevTranscriptRef.current = voice.transcript;
      if (takes > 0) {
        // For subsequent takes, combine the saved base with current voice text
        // so previous takes aren't lost. handleStopRecording will do the real append.
        const live = voice.transcript.trim();
        setTranscript(
          live
            ? baseTranscriptRef.current.trimEnd() + ' ' + live
            : baseTranscriptRef.current,
        );
      } else {
        setTranscript(voice.transcript);
      }
    }
  }, [voice.isRecording, voice.transcript, setTranscript, takes]);

  const handleStartRecording = async () => {
    setError(null);
    setPhase('recording');
    baseTranscriptRef.current = '';
    try {
      await voice.start();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not start recording';
      setError(msg);
      // Stay in current phase rather than going to idle if we have data
      if (!transcript.trim()) {
        setPhase('idle');
      } else {
        setPhase('recorded');
      }
    }
  };

  const handleStopRecording = async () => {
    const finalTranscript = await voice.stop();

    // Store audio blob if available
    if (voice.lastBlob) {
      addAudioBlob(voice.lastBlob);
    }

    // Fallback path may briefly show "transcribing" spinner
    if (voice.isTranscribing) {
      setPhase('transcribing');
    }

    if (takes > 0) {
      // Combine base (previous takes) with this take's final transcript.
      // The useEffect was showing a live preview of this during recording,
      // but we set the definitive value here with the final (non-interim) text.
      const base = baseTranscriptRef.current;
      const combined = finalTranscript.trim()
        ? base.trimEnd() + ' ' + finalTranscript.trimStart()
        : base;
      setTranscript(combined);
    } else {
      setTranscript(finalTranscript);
    }

    incrementTakes();

    if (finalTranscript.trim() || transcript.trim()) {
      // Go to 'recorded' phase — user chooses when to extract
      setPhase('recorded');
    } else {
      setError('No speech detected in recording');
      setPhase('idle');
    }
  };

  const handleRecordMore = async () => {
    setError(null);
    setPhase('recording');
    // Snapshot the current transcript so the useEffect can show
    // "previous takes + live voice" without losing anything.
    baseTranscriptRef.current = transcript;
    try {
      voice.resetTranscript();
      await voice.start();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not start recording';
      setError(msg);
      setPhase('recorded');
    }
  };

  const formatCardsAsText = (cardList: typeof cards): string => {
    return cardList
      .map((card) => {
        let text = `${card.title}\n${card.body}`;
        if (card.sub_ideas && card.sub_ideas.length > 0) {
          const subs = card.sub_ideas
            .map((sub) => `  - ${sub.title}: ${sub.body}`)
            .join('\n');
          text += '\n' + subs;
        }
        return text;
      })
      .join('\n\n');
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
      const normalized = result.cards.map((c) => ({
        ...c,
        sub_ideas: c.sub_ideas || [],
      }));
      setCards(normalized);

      // Append extracted ideas as paragraphs to the transcript
      const ideasText = formatCardsAsText(normalized);
      if (ideasText) {
        setTranscript(text.trimEnd() + '\n\n--- Key Ideas ---\n\n' + ideasText);
      }

      setPhase('review');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Idea extraction failed';
      setError(message);
      // Preserve transcript — go to 'recorded' not 'idle'
      setPhase('recorded');
    }
  };

  const handleReadBack = async () => {
    if (isPlaying || isLoading) {
      stopReadAloud();
    } else {
      await speak(transcript);
    }
  };

  const handlePlayAudio = () => {
    // Stop any current playback first
    if (playingAudioRef.current) {
      playingAudioRef.current.pause();
      playingAudioRef.current = null;
      setIsPlayingAudio(false);
      return;
    }

    if (audioUrls.length > 0) {
      const audio = new Audio(audioUrls[audioUrls.length - 1]);
      playingAudioRef.current = audio;
      setIsPlayingAudio(true);
      audio.onended = () => {
        playingAudioRef.current = null;
        setIsPlayingAudio(false);
      };
      audio.play();
    }
  };

  const handleContinueToMindMap = () => {
    if (onNavigateToMindMap) {
      onNavigateToMindMap();
    }
  };

  const handleStartBrainstorm = async () => {
    setError(null);
    setPhase('brainstorming');
    setBrainstormActive(true);
    await brainstorm.startBrainstorm();
  };

  const handleEndBrainstorm = async () => {
    // Build brainstorm conversation text and append to transcript
    const history = brainstorm.conversationHistory;
    if (history.length > 0) {
      const brainstormText = history
        .map((entry) => {
          const label = entry.role === 'user' ? 'Me' : 'AI';
          return `${label}: ${entry.content}`;
        })
        .join('\n');

      const separator = transcript.trim() ? '\n\n--- Brainstorm ---\n' : '';
      appendTranscript(separator + brainstormText);
    }

    brainstorm.stopBrainstorm();
    setBrainstormActive(false);

    // Use the updated transcript (original + brainstorm) for extraction
    const fullTranscript = transcript + (history.length > 0
      ? (transcript.trim() ? '\n\n--- Brainstorm ---\n' : '') +
        history.map((e) => `${e.role === 'user' ? 'Me' : 'AI'}: ${e.content}`).join('\n')
      : '');

    if (fullTranscript.trim()) {
      setPhase('extracting');
      try {
        const result = await api.extractIdeas(fullTranscript);
        const extractedCards = result.cards.map((c) => ({
          ...c,
          sub_ideas: c.sub_ideas || [],
        }));
        const merged = mergeCards(cards, extractedCards);
        setCards(merged);

        // Append extracted ideas as paragraphs to the transcript
        const ideasText = formatCardsAsText(merged);
        if (ideasText) {
          setTranscript(fullTranscript.trimEnd() + '\n\n--- Key Ideas ---\n\n' + ideasText);
        }

        setPhase('review');
      } catch {
        // Keep brainstorm cards if extraction fails
        setPhase('review');
      }
    } else {
      setPhase(cards.length > 0 ? 'review' : 'recorded');
    }
  };

  const handleVisionCapture = async (base64: string, mimeType: string) => {
    const previousPhase = phase;
    setIsVisionProcessing(true);
    setPhase('extracting');
    setError(null);

    try {
      const result = await api.extractIdeasFromImage(base64, mimeType);
      const normalized = result.cards.map((c) => ({
        ...c,
        sub_ideas: c.sub_ideas || [],
      }));

      if (cards.length > 0) {
        const merged = mergeCards(cards, normalized);
        setCards(merged);
      } else {
        appendCards(normalized);
      }

      setShowVisionCapture(false);
      setPhase('review');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Image extraction failed';
      setError(message);
      setPhase(previousPhase === 'extracting' ? 'idle' : previousPhase);
    } finally {
      setIsVisionProcessing(false);
    }
  };

  const isBrainstorming = phase === 'brainstorming';

  const showThoughtCards =
    phase === 'extracting' ||
    phase === 'review' ||
    (phase === 'recording' && cards.length > 0) ||
    (isBrainstorming && cards.length > 0);
  const canContinue = phase === 'review' && cards.length > 0;
  const isRecording = voice.isRecording;

  return (
    <div className="capture-mode">
      <div className="capture-area anim">
        <div className="capture-hero anim anim-d1">
          <h2>Capture Your Ideas</h2>
          <p>Type or tap the microphone and talk freely. We'll organize your thoughts into cards you can rearrange.</p>
        </div>

        <div className="mic-ring-wrapper">
          <div
            ref={radialWaveRef}
            className={`radial-wave ${isRecording ? 'active' : ''}`}
            aria-hidden="true"
          >
            {Array.from({ length: 16 }, (_, i) => (
              <span key={i} className="radial-bar" />
            ))}
          </div>
          <button
            className={`big-mic ${isRecording ? 'recording' : ''}`}
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            disabled={phase === 'transcribing' || phase === 'extracting' || isBrainstorming}
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
        </div>

        {!isRecording && !isBrainstorming && phase !== 'transcribing' && phase !== 'extracting' && (
          <div
            className={`capture-vision-pill${showVisionCapture ? ' open' : ''}${!showVisionCapture && visionMounted ? ' closing' : ''}`}
            role="group"
          >
            <button
              className="capture-vision-pill-trigger"
              onClick={() => setShowVisionCapture(true)}
              aria-label="Snap a photo"
              aria-expanded={showVisionCapture}
              tabIndex={showVisionCapture ? -1 : 0}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              Snap a photo
            </button>
            <div className="capture-vision-pill-content">
              {visionMounted && (
                <VisionCapturePanel
                  onCapture={handleVisionCapture}
                  isProcessing={isVisionProcessing}
                  onCancel={handleVisionClose}
                />
              )}
            </div>
          </div>
        )}

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
          <span className="vstatus anim">
            Listening...{takes > 0 ? ` (take ${takes + 1})` : ''}
          </span>
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
            {(phase === 'recorded' || phase === 'idle') && transcript.trim() && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleExtractIdeas()}
              >
                Try Again
              </button>
            )}
          </div>
        )}

        <div className={`capture-transcript ${transcript ? 'has-text' : ''}`}>
          <textarea
            className="transcript-textarea"
            value={transcript}
            onChange={(e) => {
              setTranscript(e.target.value);
              // Transition to 'recorded' so action buttons appear when user types
              if (e.target.value.trim() && phase === 'idle') {
                setPhase('recorded');
              }
              // If user clears all text, go back to idle
              if (!e.target.value.trim() && phase === 'recorded') {
                setPhase('idle');
              }
            }}
            placeholder="Type or speak your ideas here..."
            aria-label="Voice transcript"
            spellCheck={false}
            readOnly={isBrainstorming}
          />
        </div>

        {/* Multi-session controls: shown in 'recorded' phase */}
        {phase === 'recorded' && (
          <div className="capture-actions anim">
            <button
              className="btn btn-secondary"
              onClick={handleRecordMore}
            >
              Record More
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleExtractIdeas()}
              disabled={!transcript.trim()}
            >
              Extract Ideas
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleStartBrainstorm}
              disabled={micDenied}
              aria-label="Start brainstorming with AI"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Brainstorm with AI
            </button>
            {audioUrls.length > 0 && (
              <button
                className="btn btn-ghost"
                onClick={handlePlayAudio}
                aria-label={isPlayingAudio ? 'Stop playback' : 'Play last recording'}
              >
                {isPlayingAudio ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <rect x="6" y="5" width="4" height="14" rx="1" />
                    <rect x="14" y="5" width="4" height="14" rx="1" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                )}
              </button>
            )}
          </div>
        )}

        {/* Brainstorm panel: shown during brainstorming phase */}
        {isBrainstorming && (
          <BrainstormPanel
            loopState={brainstorm.loopState}
            conversationHistory={brainstorm.conversationHistory}
            currentUtterance={brainstorm.currentUtterance}
            autoProbe={brainstormAutoProbe}
            onToggleAutoProbe={setBrainstormAutoProbe}
            onAskAi={brainstorm.triggerAiTurn}
            onEndBrainstorm={handleEndBrainstorm}
          />
        )}

        {/* Live idea counter during recording */}
        {isRecording && cards.length > 0 && (
          <span className="capture-live-count anim" aria-live="polite">
            {cards.length} idea{cards.length !== 1 ? 's' : ''} found
          </span>
        )}

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

    </div>
  );
}
