/**
 * Editable transcript panel for Capture Mode.
 */

import { useCaptureStore } from '../../stores/captureStore';

interface TranscriptPanelProps {
  isLoading?: boolean;
}

export function TranscriptPanel({ isLoading }: TranscriptPanelProps) {
  const transcript = useCaptureStore((s) => s.transcript);
  const setTranscript = useCaptureStore((s) => s.setTranscript);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setTranscript(e.target.value);
  };

  return (
    <div className="transcript-panel">
      <h3 className="transcript-panel-title">Transcript</h3>

      {transcript || isLoading ? (
        <textarea
          className="transcript-textarea"
          value={transcript}
          onChange={handleChange}
          readOnly={isLoading}
          placeholder="Your transcript will appear here..."
          aria-label="Voice transcript"
          spellCheck={false}
        />
      ) : (
        <div className="transcript-empty" role="status">
          <p>Click the microphone to start recording.</p>
          <p className="transcript-hint">Speak freely — your ideas will be organized automatically.</p>
        </div>
      )}
    </div>
  );
}
