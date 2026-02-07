# Text-to-Speech — Read Aloud

## Purpose

Read Aloud is one of the most requested features by dyslexic users. Hearing text helps catch errors that eyes miss. DysLex AI uses MagpieTTS via NVIDIA NIM to provide natural, human-sounding voice output.

**Key insight**: Many dyslexic users proofread by ear, not by eye. Read Aloud makes this seamless.

## User Experience

### How It Works
1. User clicks "Read Aloud" button
2. Natural voice begins reading
3. Current word/sentence is highlighted
4. User can pause, resume, or stop anytime
5. Speed is adjustable

### Controls
```
┌─────────────────────────────────────┐
│  ▶️ Play   ⏸ Pause   ⏹ Stop        │
│  🐢 ─────○───── 🐇   Speed: 0.9x   │
└─────────────────────────────────────┘
```

## Technical Implementation

### Frontend Hook

```typescript
// frontend/src/hooks/useTextToSpeech.ts
export function useTextToSpeech(options = {}) {
  const { rate = 0.9, pitch = 1, volume = 1 } = options;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const speak = useCallback((text: string, voiceName?: string) => {
    // For browser fallback: Web Speech API
    // For quality: Call backend MagpieTTS endpoint
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  const pause = useCallback(() => {
    window.speechSynthesis.pause();
    setIsPaused(true);
  }, []);

  const resume = useCallback(() => {
    window.speechSynthesis.resume();
    setIsPaused(false);
  }, []);

  return { speak, stop, pause, resume, isSpeaking, isPaused };
}
```

### Backend TTS Service

```python
# backend/app/services/tts_service.py
async def text_to_speech(text: str, voice: str = "default") -> str:
    """Convert text to speech using MagpieTTS via NVIDIA NIM."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nvidia_nim_base_url}/audio/speech",
            headers={"Authorization": f"Bearer {settings.nvidia_nim_api_key}"},
            json={
                "model": "nvidia/magpietts",
                "input": text,
                "voice": voice,
                "response_format": "mp3",
            },
        )
        # Save audio and return URL
        return "/audio/generated.mp3"

def get_available_voices() -> list[dict]:
    """Get list of available TTS voices."""
    return [
        {"id": "default", "name": "Default", "language": "en-US"},
        {"id": "slow", "name": "Slow Reader", "language": "en-US"},
    ]
```

## MagpieTTS Features

### Why MagpieTTS?
- **Natural prosody**: Sounds like a real person
- **Emotion handling**: Appropriate intonation
- **No hallucinations**: Monotonic alignment prevents skipped/repeated words
- **Multilingual**: English, Spanish, German, French, Vietnamese, Italian, Chinese

### Voice Options
| Voice | Description | Best For |
|-------|-------------|----------|
| Default | Natural, clear reading | General use |
| Slow Reader | Slower pace, clearer enunciation | Learning, proofreading |

## Word Highlighting (Future)

When reading aloud, highlight the current word:

```typescript
// Sync audio playback with word highlighting
interface WordTiming {
  word: string;
  start: number;  // seconds
  end: number;
}

function highlightCurrentWord(timings: WordTiming[], currentTime: number) {
  const current = timings.find(t => currentTime >= t.start && currentTime < t.end);
  // Apply highlight style to current word
}
```

## API Endpoints

```python
# backend/app/api/routes/voice.py

@router.post("/tts")
async def synthesize_speech(text: str, voice: str = "default"):
    """Convert text to speech using MagpieTTS."""
    audio_url = await text_to_speech(text, voice)
    return {"audio_url": audio_url}

@router.get("/voices")
async def list_voices():
    """List available TTS voices."""
    return {"voices": get_available_voices()}
```

## Key Files

### Frontend
- `frontend/src/hooks/useTextToSpeech.ts` — TTS hook
- `frontend/src/components/WritingModes/PolishMode.tsx` — Uses TTS

### Backend
- `backend/app/services/tts_service.py` — MagpieTTS integration
- `backend/app/api/routes/voice.py` — Voice endpoints

## Fallback Strategy

1. **Try**: MagpieTTS via NVIDIA NIM (highest quality)
2. **Fallback**: Browser Web Speech API (works offline)

```typescript
const speak = useCallback((text: string) => {
  if (preferNativeTTS || !navigator.onLine) {
    // Use browser speechSynthesis
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  } else {
    // Call backend MagpieTTS endpoint
    fetch('/api/voice/tts', { method: 'POST', body: JSON.stringify({ text }) });
  }
}, []);
```

## Accessibility Requirements

- **Keyboard control**: Play/pause/stop via keyboard
- **Speed adjustment**: User-controlled pace
- **Visual indicator**: Show when audio is playing
- **No auto-play**: User initiates read aloud
- **Stop on navigation**: Audio stops when leaving page

## Integration Points

- **Polish Mode**: Primary use for proofreading
- **Draft Mode**: Optional read-back while writing
- **Capture Mode**: Read back transcribed text

## Performance Considerations

- Stream audio rather than waiting for full generation
- Cache frequently read content
- Pre-generate common words/phrases
- Limit text length per request (~500 words)

## Status

- [x] useTextToSpeech hook implemented
- [x] Browser Speech API fallback
- [ ] MagpieTTS NIM integration
- [ ] Word-level highlighting
- [ ] Voice selection UI
- [ ] Speed control UI
