# Text-to-Speech — Read Aloud

## Purpose

Read aloud is a core accessibility feature. Dyslexic users proofread by ear, not by eye. Uses MagpieTTS via NVIDIA Riva with browser Web Speech API fallback.

## Architecture

### Backend: Two Protocols

`backend/app/services/tts_service.py` auto-detects cloud vs self-hosted:

| Protocol | When | Client |
|----------|------|--------|
| **gRPC** | Cloud API (`integrate.api.nvidia.com`) | `grpc_tts_client.py` |
| **HTTP** | Self-hosted Riva NIM | Direct `httpx` POST |

#### Content-Addressed Caching

Audio files cached by SHA-256 hash of `(voice, text)`:
- Cache hit → serve existing WAV file (zero latency)
- Cache miss → call API, save as `{hash}.wav`, store `.meta` for cleanup
- Hourly cleanup task in `main.py` removes old cached files

#### Batch Synthesis

`batch_text_to_speech(sentences, voice)` processes multiple sentences:
- Partitions into cached/uncached
- Only calls API for uncached sentences
- Returns `[{index, audio_url, cached}]`

#### Voice Mapping

| Friendly ID | Riva Voice Name |
|-------------|----------------|
| `default` / `aria` | `Magpie-Multilingual.EN-US.Aria` |
| `diego` | `Magpie-Multilingual.ES-US.Diego` |
| `louise` | `Magpie-Multilingual.FR-FR.Louise` |

### Frontend: Sentence-Level Playback

`frontend/src/hooks/useReadAloud.ts`:
- Splits text into sentences (`ttsSentenceCache.splitIntoSentences()`)
- Batches API calls (50 sentences at a time)
- AudioContext for playback with rate control
- 150ms silence gaps between sentences
- Fallback: MagpieTTS → browser Web Speech API
- Respects `voiceEnabled` setting
- Fires `dyslex-tts-used` event for prewarmer activation

### TTS Prewarmer

`frontend/src/hooks/useTtsPrewarmer.ts`:
- Activates after user clicks "Read Aloud" at least once
- Pre-generates audio for changed sentences during idle (2s+)
- 3s debounce between batches, max 20 sentences per batch
- Cancellable requests

### Sentence Audio Cache

`frontend/src/services/ttsSentenceCache.ts`:
- LRU cache (max 200 entries)
- Voice-aware SHA-256 hashing
- Abbreviation-safe sentence splitting (handles Mr., Dr., etc.)

## Key Files

| File | Role |
|------|------|
| `backend/app/services/tts_service.py` | Main TTS service (cloud + self-hosted) |
| `backend/app/services/grpc_tts_client.py` | Cloud gRPC client (raw protobuf) |
| `frontend/src/hooks/useReadAloud.ts` | Frontend TTS hook |
| `frontend/src/hooks/useTtsPrewarmer.ts` | Background cache warming |
| `frontend/src/services/ttsSentenceCache.ts` | LRU sentence cache |

## Integration Points

- [Polish Mode](../modes/polish-mode.md): Primary read-aloud consumer
- [Brainstorm Mode](../modes/brainstorm-mode.md): AI voice responses
- [NIM Integration](nim-integration.md): API configuration

## Status

- [x] MagpieTTS via gRPC (cloud) and HTTP (self-hosted)
- [x] Content-addressed file caching
- [x] Batch synthesis
- [x] Frontend sentence-level playback with AudioContext
- [x] TTS prewarmer for idle-time cache warming
- [x] Browser Web Speech API fallback
- [ ] Word-level highlighting during playback
- [ ] Voice selection UI
