# Capture Mode — Voice-to-Thought

## Purpose

Voice-first idea capture. Users speak freely, the AI transcribes in real-time, extracts idea clusters as thought cards, and supports voice-to-voice brainstorming.

## User Experience

1. User taps the microphone button (large, obvious)
2. Waveform visualization shows audio activity
3. Speech transcribed via Web Speech API (real-time interim results)
4. User stops recording; transcript appears in editable textarea
5. "Extract Ideas" processes transcript into thought cards
6. Optional: brainstorm mode for voice-to-voice AI conversation
7. Cards transfer to Mind Map mode

## Technical Implementation

### Frontend Component

`frontend/src/components/WritingModes/CaptureMode.tsx`:
- Big microphone button with waveform bars (`useWaveformBars`)
- Transcript textarea with edit capability
- `ThoughtCardGrid` for displaying extracted ideas
- `BrainstormPanel` integration for voice-to-voice AI
- Read-aloud speaker button (`useReadAloud`)
- Multi-take recording support

### Voice Input

`frontend/src/hooks/useVoiceInput.ts` — Low-level Web Speech API wrapper:
- Auto-punctuation (capitalize first letter, add period)
- Interim text display while speaking
- Continuous mode with auto-restart on silence
- Error suppression for "no-speech" and "aborted"

Wrapped by `useCaptureVoice` hook for capture-mode-specific behavior.

### Idea Extraction

Uses `api.extractIdeas()` to send transcript to backend LLM for clustering. Supports incremental extraction (`useIncrementalExtraction`) — only processes new transcript text since last extraction.

### Brainstorm Integration

See [brainstorm-mode.md](brainstorm-mode.md) for the full voice-to-voice state machine.

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/WritingModes/CaptureMode.tsx` | Main component |
| `frontend/src/hooks/useVoiceInput.ts` | Web Speech API wrapper |
| `frontend/src/hooks/useBrainstormLoop.ts` | Voice-to-voice state machine |
| `frontend/src/stores/captureStore.ts` | Per-document capture state (Zustand, persisted) |
| `frontend/src/hooks/useReadAloud.ts` | Read-back of transcripts |

## State Management

`captureStore.ts` (Zustand with user-scoped persistence):
- Per-document sessions (survives mode switches)
- State: `phase`, `transcript`, `cards`, `takes`, `brainstormActive`
- Transient state (audio blobs, URLs) not persisted
- Auto-migration from v0 (global) to v1 (per-document)
- Subscribes to `documentStore` for cleanup on document delete

## Integration Points

- [Mind Map Mode](mindmap-mode.md): Thought cards transfer as nodes
- [Brainstorm Mode](brainstorm-mode.md): Voice-to-voice AI conversation
- [User-Scoped Storage](../frontend/user-scoped-storage.md): Per-user persistence

## Status

- [x] Voice input with Web Speech API
- [x] Waveform visualization
- [x] Transcript editing
- [x] Idea extraction via LLM
- [x] Incremental extraction
- [x] Brainstorm integration
- [x] Multi-take recording
- [x] Per-document persistence
- [ ] Backend faster-whisper STT (higher accuracy alternative)
