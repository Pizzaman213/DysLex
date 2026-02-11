# Brainstorm Mode — Voice-to-Voice AI Conversation

## Purpose

Voice-to-voice brainstorming within Capture Mode. The user speaks, the AI responds with audio, and ideas are automatically captured as thought cards. Designed for dyslexic thinkers who express ideas better verbally.

## User Experience

1. User activates brainstorm from Capture Mode
2. Speaks an idea or question
3. AI responds with voice (MagpieTTS) after a natural pause
4. Conversation continues back-and-forth
5. AI extracts sub-ideas and new cards from responses
6. All generated ideas appear as thought cards

## State Machine

`frontend/src/hooks/useBrainstormLoop.ts` implements a state machine:

```
IDLE → LISTENING → PAUSE_DETECTED → AI_THINKING → AI_SPEAKING → LISTENING
                        ↓                              ↓
                   WAITING_MANUAL                (user interrupts → LISTENING)
                        ↓
                    (Ask AI btn)
```

**Two trigger modes:**
- **Auto-probe**: AI responds automatically after a pause in speech
- **Manual**: User clicks "Ask AI" button to trigger response

### User Interruption

If user starts speaking while AI is talking, TTS stops immediately and transitions back to LISTENING state.

## Technical Implementation

### Frontend Hook

`useBrainstormLoop.ts` exports:
- `state` — Current state machine state
- `startBrainstorm()` / `stopBrainstorm()` — Session control
- `askAI()` — Manual trigger
- `conversationHistory` — Full conversation log

**Key behaviors:**
- Reuses shared voice instance (Chrome SpeechRecognition limitation)
- MagpieTTS audio playback with browser TTS fallback
- Sub-idea and new card generation from AI responses
- Integration with `captureStore` for card management

### Backend Service

`backend/app/services/brainstorm_service.py`:
- `BrainstormService.process_turn()` — Processes single brainstorm turn
- Builds proper messages array (system + conversation history + current utterance)
- Calls NIM API for response generation
- Generates TTS audio for AI reply via `tts_service`
- Falls back to reasoning field if content is empty
- Graceful error handling with fallback responses

### Backend Prompts

`backend/app/core/brainstorm_prompts.py` — System prompt for brainstorm conversations (warm, encouraging, idea-generative).

## Key Files

| File | Role |
|------|------|
| `frontend/src/hooks/useBrainstormLoop.ts` | State machine orchestration |
| `frontend/src/components/WritingModes/CaptureMode.tsx` | UI integration (BrainstormPanel) |
| `frontend/src/stores/captureStore.ts` | `brainstormActive`, `brainstormAutoProbe` state |
| `backend/app/services/brainstorm_service.py` | LLM + TTS turn processing |
| `backend/app/core/brainstorm_prompts.py` | System prompt construction |

## Integration Points

- [Capture Mode](capture-mode.md): Embedded within capture mode UI
- [Voice Input](../backend/voice-input.md): Shared Web Speech API instance
- [TTS](../backend/text-to-speech.md): MagpieTTS for AI voice responses
- [Capture Store](capture-mode.md): Cards generated from AI responses

## Status

- [x] State machine with all transitions
- [x] Auto-probe and manual trigger modes
- [x] User interruption detection
- [x] MagpieTTS audio playback with browser fallback
- [x] Conversation history tracking
- [x] Sub-idea and card generation
- [x] Backend service with NIM API integration
