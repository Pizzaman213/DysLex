interface VoiceBarProps {
  isRecording: boolean;
  isTranscribing: boolean;
  analyserNode?: AnalyserNode | null;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onTranscript?: (text: string) => void;
  compact?: boolean;
}

export function VoiceBar({
  isRecording,
  isTranscribing,
  onStartRecording,
  onStopRecording,
  compact = false,
}: VoiceBarProps) {
  const handleToggle = () => {
    if (isRecording) {
      onStopRecording();
    } else {
      onStartRecording();
    }
  };

  const barClasses = `voice-bar ${isRecording ? 'voice-bar-active' : ''} ${compact ? 'voice-bar-compact' : ''}`;

  return (
    <div className={barClasses}>
      <button
        className={compact ? 'vb' : 'voice-btn'}
        onClick={handleToggle}
        disabled={isTranscribing}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        aria-pressed={isRecording}
      >
        <span className="voice-icon" aria-hidden="true">
          {isRecording ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
              <rect x="4" y="4" width="16" height="16" rx="2" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </span>
        {!compact && (
          <span className="voice-label">{isRecording ? 'Stop' : 'Record'}</span>
        )}
      </button>

      {isRecording && (
        <div className={`${compact ? 'wave' : 'big-wave'} active`} aria-live="polite">
          {(compact ? [1,2,3,4,5] : [1,2,3,4,5,6,7]).map((i) => (
            <span key={i} />
          ))}
          <span className="sr-only">Recording in progress</span>
        </div>
      )}

      {!isRecording && !isTranscribing && !compact && (
        <div className="big-wave">
          {[1,2,3,4,5,6,7].map((i) => (
            <span key={i} />
          ))}
        </div>
      )}

      {isTranscribing && (
        <div className="voice-indicator" aria-live="polite">
          <div className="capture-spinner" aria-hidden="true" />
          <span>Transcribing...</span>
        </div>
      )}

      {isRecording && (
        <span className="vstatus">Listening...</span>
      )}
    </div>
  );
}
