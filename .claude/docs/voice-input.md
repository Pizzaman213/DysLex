# Voice Input — Speech-to-Text

## Purpose

Voice input is a first-class feature in DysLex AI. Dyslexic thinkers often express ideas better verbally than in writing. Speech-to-text removes the friction of typing and lets ideas flow naturally.

**Key insight**: The best writing tool for some dyslexic users is one that doesn't require writing at all — at least not initially.

## User Experience

### How It Works
1. User taps microphone button
2. Visual indicator shows "Listening..."
3. Speech is transcribed in real-time (text appears as they speak)
4. User taps again to stop
5. Transcript is ready for editing or organizing

### Voice Bar UI
```
┌─────────────────────────────────────┐
│  🎤 Speak       ○ ○ ○ Listening...  │
└─────────────────────────────────────┘
```

- Large, obvious microphone button
- Animated indicator when active
- Clear visual feedback throughout

## Technical Implementation

### Browser Speech API (Fallback)

```typescript
// frontend/src/hooks/useVoiceInput.ts
export function useVoiceInput(options = {}) {
  const { language = 'en-US', continuous = true } = options;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
      setIsSupported(true);
      const recognition = new SpeechRecognition();
      recognition.lang = language;
      recognition.continuous = continuous;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        // Process interim and final results
        // Update transcript in real-time
      };

      recognitionRef.current = recognition;
    }
  }, []);

  return { isListening, transcript, startListening, stopListening, isSupported };
}
```

### NVIDIA NIM faster-whisper (Primary)

For better accuracy, especially with diverse accents and background noise:

```python
# backend/app/services/stt_service.py
async def speech_to_text(audio: UploadFile) -> str:
    """Convert speech to text using faster-whisper via NVIDIA NIM."""
    # Upload audio to NIM endpoint
    # Process with faster-whisper model
    # Return high-accuracy transcript

async def transcribe_with_timestamps(audio: UploadFile) -> dict:
    """Transcribe with word-level timestamps."""
    # Used for read-along highlighting
    return {
        "text": "Full transcript here",
        "words": [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0}
        ],
        "language": "en"
    }
```

### Voice Bar Component

```typescript
// frontend/src/components/Shared/VoiceBar.tsx
export function VoiceBar({ onStart, onStop }) {
  const { isListening, isSupported } = useVoiceInput();

  if (!isSupported) {
    return <div className="voice-bar-unsupported">Voice not supported</div>;
  }

  return (
    <div className={`voice-bar ${isListening ? 'active' : ''}`}>
      <button
        onClick={isListening ? onStop : onStart}
        aria-label={isListening ? 'Stop listening' : 'Start voice input'}
      >
        <span className="voice-icon">{isListening ? '⏹' : '🎤'}</span>
        <span className="voice-label">{isListening ? 'Stop' : 'Speak'}</span>
      </button>

      {isListening && (
        <div className="voice-indicator" aria-live="polite">
          <span className="voice-pulse" />
          <span>Listening...</span>
        </div>
      )}
    </div>
  );
}
```

## API Endpoints

```python
# backend/app/api/routes/voice.py

@router.post("/stt")
async def transcribe_audio(audio: UploadFile, user_id: CurrentUserId):
    """Convert speech to text using faster-whisper."""
    transcript = await speech_to_text(audio)
    return {"transcript": transcript}
```

## Key Files

### Frontend
- `frontend/src/hooks/useVoiceInput.ts` — Voice capture hook
- `frontend/src/components/Shared/VoiceBar.tsx` — Mic button UI
- `frontend/src/components/WritingModes/CaptureMode.tsx` — Uses voice input

### Backend
- `backend/app/services/stt_service.py` — faster-whisper integration
- `backend/app/api/routes/voice.py` — Voice endpoints

## Fallback Strategy

1. **Try**: NVIDIA NIM faster-whisper (highest accuracy)
2. **Fallback**: Browser Web Speech API (works offline)
3. **Last resort**: Show "Voice not supported" message

## Accessibility Requirements

- **Large touch target**: Mic button 44x44px minimum
- **Visual feedback**: Clear "listening" state
- **Keyboard accessible**: Can trigger with keyboard
- **Screen reader**: Announces state changes
- **No time pressure**: User controls when to stop
- **Error handling**: Graceful failure messages

## Privacy Considerations

- Audio can be processed locally (Web Speech API)
- Server-side processing via NIM is encrypted
- Audio is not stored after transcription
- User controls when mic is active

## Integration Points

- **Capture Mode**: Primary use of voice input
- **Draft Mode**: Voice-to-text option in toolbar
- **Polish Mode**: Voice notes for revision ideas

## Supported Languages

faster-whisper supports 100+ languages. DysLex AI initially targets:
- English (en)
- Spanish (es)
- French (fr)
- German (de)

## Status

- [x] useVoiceInput hook implemented
- [x] VoiceBar component created
- [x] Browser Speech API integration
- [ ] NVIDIA NIM faster-whisper integration
- [ ] Timestamp support for highlighting
- [ ] Multi-language support
