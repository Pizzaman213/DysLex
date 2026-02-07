# Voice Services Verification Guide

## Quick Start Testing

### 1. Start the Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Verify Static Files Mount
```bash
curl http://localhost:8000/health
# Should return {"status": "healthy", ...}
```

### 3. Test TTS Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/voice/speak \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"text": "Hello world", "voice": "default"}'

# Response: {"status": "success", "data": {"audio_url": "/audio/SOME-UUID.mp3"}}
```

### 4. Verify Audio File Created
```bash
ls -lh backend/storage/audio/
# Should show .mp3 and .meta files
```

### 5. Access Audio in Browser
```
http://localhost:8000/audio/SOME-UUID.mp3
```

## Testing STT Service

### Test Unified Transcription
```bash
# Both endpoints should work identically now
curl -X POST http://localhost:8000/api/v1/voice/transcribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.webm"

curl -X POST http://localhost:8000/api/v1/capture/transcribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.webm"
```

## Testing WebSocket Streaming

### Using websocat (CLI tool)
```bash
# Install: brew install websocat
echo '{"type":"start","sample_rate":48000}' | websocat ws://localhost:8000/api/v1/voice/stream
```

### Using Browser Console
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/voice/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({type: 'start', sampleRate: 48000}));
  console.log('✓ Connected');
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};

// Send audio chunks (from MediaRecorder)
// ws.send(audioBlob.arrayBuffer());

// Stop streaming
ws.send(JSON.stringify({type: 'stop'}));
```

### Using Frontend Hook
```typescript
import { useStreamingTranscription } from '@/hooks/useStreamingTranscription';

function TestComponent() {
  const { isStreaming, transcript, startStreaming, stopStreaming } = useStreamingTranscription();
  
  return (
    <div>
      <button onClick={startStreaming}>Start</button>
      <button onClick={stopStreaming}>Stop</button>
      <p>{transcript}</p>
    </div>
  );
}
```

## Testing Nemotron Parsing

### Test Deep Analysis
```bash
curl -X POST http://localhost:8000/api/v1/correct \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "text": "I wnet to the stor becuase I neaded milk.",
    "mode": "deep"
  }'

# Should return parsed Correction objects with:
# - original, correction, error_type, position (optional), confidence, explanation
```

### Test with Malformed JSON
The parser should gracefully handle:
- Direct JSON arrays: `[{"original": "teh", "correction": "the"}]`
- Markdown fences: ` ```json\n[...]\n``` `
- Embedded JSON: `Here are the corrections: [...]`
- Malformed responses: Returns empty array, logs warning

## Environment Variables

Ensure these are set in `.env`:
```bash
NVIDIA_NIM_API_KEY=your-key-here
TTS_AUDIO_DIR=storage/audio
TTS_AUDIO_BASE_URL=/audio
TTS_CACHE_TTL=3600
TTS_CLEANUP_ENABLED=true
```

## File Permissions

Verify the backend can write to storage:
```bash
ls -ld backend/storage/audio
# Should be writable by backend process user
```

## Cleanup Testing

### Manual Cleanup Trigger
```python
# In Python console
from app.services.tts_service import cleanup_old_audio_files
cleanup_old_audio_files()
```

### Verify Automatic Cleanup
1. Generate TTS audio
2. Manually edit `.meta` file to be old timestamp
3. Wait for next cleanup cycle (1 hour) or trigger manually
4. Verify files deleted

## Common Issues

### WebSocket Connection Fails
- Check CORS settings allow WebSocket upgrades
- Verify no proxy blocking WebSocket connections
- Check browser console for errors

### TTS Audio Not Playing
- Verify static files mount: `app.mount("/audio", ...)`
- Check audio file exists in storage directory
- Verify correct MIME type returned (audio/mpeg)

### Transcription Returns Stub Text
- Verify `stt_service.py` is deleted
- Check imports use `transcription_service`
- Verify NVIDIA_NIM_API_KEY is set

### Nemotron Returns Empty Corrections
- Check LLM response format in logs
- Verify JSON parser handles response format
- Check Pydantic model validation errors

## Success Indicators

✅ TTS returns unique URLs, not hardcoded `/audio/generated.mp3`
✅ Audio files appear in `backend/storage/audio/`
✅ Both `/voice/transcribe` and `/capture/transcribe` work
✅ WebSocket accepts connections and echoes messages
✅ Nemotron returns parsed Correction objects, not empty lists
✅ Old audio files are cleaned up automatically

## Next Integration Steps

1. Add WebSocket authentication (JWT in query param)
2. Integrate `useStreamingTranscription` into Draft Mode UI
3. Add streaming transcription button to editor toolbar
4. Display partial transcripts in real-time
5. Insert final transcript at cursor position
6. Add unit tests for all new services
7. Add integration tests for full voice workflows
