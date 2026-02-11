# Voice Input — Speech-to-Text

## Purpose

Voice-first input for dyslexic thinkers who express ideas better verbally. Uses the browser's Web Speech API — no backend STT service required.

## Implementation

### Frontend Only

`frontend/src/hooks/useVoiceInput.ts`:
- **Web Speech API** (`SpeechRecognition` / `webkitSpeechRecognition`)
- Real-time interim results while speaking
- Auto-punctuation (capitalize first letter, add period)
- Continuous mode with auto-restart on silence
- Error suppression for "no-speech" and "aborted" events

Returns:
```typescript
{ isListening, transcript, interimText, isSupported, startListening, stopListening, resetTranscript }
```

### Wrapper Hook

`useCaptureVoice` wraps `useVoiceInput` with capture-mode-specific behavior (waveform integration, take management).

### No Backend STT Service

The current implementation relies entirely on the browser's Web Speech API. There is no `stt_service.py` or `/api/voice/stt` endpoint. A backend faster-whisper integration is planned for higher accuracy.

## Consumers

| Mode | Usage |
|------|-------|
| Capture Mode | Primary voice input for idea capture |
| Mind Map Mode | Quick node addition via voice |
| Draft Mode | Voice-to-text insertion in editor |
| Polish Mode | Voice input enabled |
| Brainstorm | Shared voice instance for conversation |

## Key Files

| File | Role |
|------|------|
| `frontend/src/hooks/useVoiceInput.ts` | Web Speech API wrapper |
| `frontend/src/components/WritingModes/CaptureMode.tsx` | Primary consumer |

## Integration Points

- [Capture Mode](../modes/capture-mode.md): Main voice input consumer
- [Brainstorm Mode](../modes/brainstorm-mode.md): Shared voice instance
- [Draft Mode](../modes/draft-mode.md): Voice-to-text in editor

## Status

- [x] Web Speech API integration
- [x] Auto-punctuation
- [x] Continuous mode
- [x] Used in all writing modes
- [ ] Backend faster-whisper integration (higher accuracy)
- [ ] Multi-language support
