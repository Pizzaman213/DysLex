import { useVoiceInput } from '../../hooks/useVoiceInput';
import { VoiceBar } from '../Shared/VoiceBar';

interface CaptureModeProps {
  onTextCapture: (text: string) => void;
}

export function CaptureMode({ onTextCapture }: CaptureModeProps) {
  const { isListening, transcript, startListening, stopListening } = useVoiceInput();

  const handleTranscriptComplete = () => {
    if (transcript) {
      onTextCapture(transcript);
    }
    stopListening();
  };

  return (
    <div className="capture-mode">
      <div className="capture-instructions" role="status">
        <h2>Voice to Thought</h2>
        <p>Speak your ideas freely. We'll capture everything.</p>
      </div>

      <VoiceBar
        isListening={isListening}
        onStart={startListening}
        onStop={handleTranscriptComplete}
      />

      {transcript && (
        <div className="transcript-preview" aria-live="polite">
          <p>{transcript}</p>
        </div>
      )}
    </div>
  );
}
