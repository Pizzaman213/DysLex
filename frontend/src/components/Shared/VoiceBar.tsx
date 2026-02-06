import { useVoiceInput } from '../../hooks/useVoiceInput';

interface VoiceBarProps {
  isListening?: boolean;
  onStart?: () => void;
  onStop?: () => void;
}

export function VoiceBar({ isListening: controlledListening, onStart, onStop }: VoiceBarProps) {
  const { isListening: internalListening, startListening, stopListening, isSupported } =
    useVoiceInput();

  const isListening = controlledListening ?? internalListening;

  const handleToggle = () => {
    if (isListening) {
      onStop ? onStop() : stopListening();
    } else {
      onStart ? onStart() : startListening();
    }
  };

  if (!isSupported) {
    return (
      <div className="voice-bar voice-bar-unsupported" role="status">
        <p>Voice input is not supported in your browser.</p>
      </div>
    );
  }

  return (
    <div className={`voice-bar ${isListening ? 'voice-bar-active' : ''}`}>
      <button
        className="voice-btn"
        onClick={handleToggle}
        aria-label={isListening ? 'Stop listening' : 'Start voice input'}
        aria-pressed={isListening}
      >
        <span className="voice-icon" aria-hidden="true">
          {isListening ? '⏹' : '🎤'}
        </span>
        <span className="voice-label">{isListening ? 'Stop' : 'Speak'}</span>
      </button>

      {isListening && (
        <div className="voice-indicator" aria-live="polite">
          <span className="voice-pulse" aria-hidden="true" />
          <span>Listening...</span>
        </div>
      )}
    </div>
  );
}
