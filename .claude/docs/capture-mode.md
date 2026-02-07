# Capture Mode — Voice-to-Thought

## Purpose

Capture Mode enables voice-first idea capture. Dyslexic thinkers often express ideas better verbally than in writing. This mode lets them speak freely, and the AI transcribes and organizes their thoughts into actionable cards.

**Key insight**: Don't make users type ideas they'll later organize. Let them talk first, structure second.

## User Experience

1. User taps the microphone button
2. Speaks freely: "I want to write about how dogs help people with anxiety. Like therapy dogs? And also just regular pets. My neighbor's dog always makes me feel better."
3. AI transcribes in real-time (text appears as they speak)
4. AI identifies idea clusters and creates draggable "thought cards"
5. User can pause, continue, or move to Mind Map mode

### What Users See
- Large microphone button (easy to tap)
- Real-time transcript appearing below
- Thought cards emerging as ideas are detected
- Visual indicator showing "Listening..." state
- No typing required

### What Users Don't See
- The speech-to-text processing
- Idea clustering algorithm
- Any technical complexity

## Technical Implementation

### Frontend Components

```typescript
// frontend/src/components/WritingModes/CaptureMode.tsx
export function CaptureMode({ onTextCapture }: CaptureModeProps) {
  const { isListening, transcript, startListening, stopListening } = useVoiceInput();

  return (
    <div className="capture-mode">
      <VoiceBar
        isListening={isListening}
        onStart={startListening}
        onStop={handleTranscriptComplete}
      />
      {transcript && <TranscriptPreview text={transcript} />}
    </div>
  );
}
```

### Voice Input Hook

```typescript
// frontend/src/hooks/useVoiceInput.ts
export function useVoiceInput(options = {}) {
  // Uses Web Speech API for browser-native STT
  // Falls back to backend faster-whisper for better accuracy

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');

  // Real-time transcription with interim results
  // Handles pause detection
  // Manages microphone permissions
}
```

### Backend STT Service

```python
# backend/app/services/stt_service.py
async def speech_to_text(audio: UploadFile) -> str:
    """Convert speech to text using faster-whisper."""
    # Process audio file
    # Run faster-whisper inference
    # Return transcript

async def transcribe_with_timestamps(audio: UploadFile) -> dict:
    """Transcribe with word-level timestamps for highlighting."""
    # Used for read-along features
```

### Idea Clustering (Future)

```python
# backend/app/services/idea_extractor.py
async def extract_ideas(transcript: str) -> list[IdeaCard]:
    """Extract discrete ideas from transcript."""
    # Use LLM to identify:
    # - Main topics
    # - Supporting points
    # - Examples
    # - Questions/uncertainties
    # Return as structured cards
```

## Key Files

### Frontend
- `frontend/src/components/WritingModes/CaptureMode.tsx` — Main component
- `frontend/src/hooks/useVoiceInput.ts` — Voice capture hook
- `frontend/src/components/Shared/VoiceBar.tsx` — Mic button UI

### Backend
- `backend/app/services/stt_service.py` — faster-whisper integration
- `backend/app/api/routes/voice.py` — Voice API endpoints

## Accessibility Requirements

- **Large touch target**: Mic button at least 44x44px
- **Visual feedback**: Clear "listening" indicator
- **Keyboard accessible**: Can start/stop with keyboard
- **Screen reader**: Announces state changes
- **No time pressure**: User controls when to stop
- **Works offline**: Browser Speech API as fallback

## Integration Points

- **Mind Map Mode**: Thought cards transfer to mind map
- **Draft Mode**: Full transcript can seed draft
- **Error Profile**: Captures natural speech patterns

## NVIDIA NIM Integration

For higher accuracy than browser Speech API:

```python
# Uses NVIDIA NIM faster-whisper endpoint
# Handles audio streaming
# Returns real-time transcription
```

## Voice UI Best Practices

1. **Obvious affordance**: The mic button should look tappable
2. **Immediate feedback**: Visual response within 100ms
3. **Error recovery**: If STT fails, save audio for retry
4. **Privacy clear**: Show when mic is active
5. **Easy stop**: Stopping should be as easy as starting

## Status

- [x] Component structure designed
- [x] Voice input hook implemented
- [x] Backend STT service placeholder
- [ ] faster-whisper NIM integration
- [ ] Idea extraction/clustering
- [ ] Thought cards UI
- [ ] Transfer to Mind Map
