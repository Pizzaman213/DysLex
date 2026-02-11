# Polish Mode — Review & Refine

## Purpose

Final review stage with full-document analysis, readability scoring, AI coach, and read-aloud. Uses Tier 2 deep analysis (Nemotron) for comprehensive suggestions.

## User Experience

1. User clicks "Polish" when draft feels complete
2. Full-document analysis runs via Tier 2 Nemotron
3. Full-page document view with zoom controls
4. Coach panel on left for writing advice
5. Polish panel on right with suggestions and readability metrics
6. Read-aloud with TTS prewarming for efficient playback

## Technical Implementation

### Main Component

`frontend/src/components/WritingModes/PolishMode.tsx`:
- Full-page document view with zoom controls
- `CoachPanel` on left side
- `PolishPanel` on right side (suggestions + readability)
- `EditorToolbar` for formatting
- Voice input enabled
- `useTtsPrewarmer` for background audio cache warming

### Deep Analysis

Backend `document_review()` in `backend/app/core/llm_orchestrator.py` always uses Tier 2:
- Sends full document to `nemotron_client.deep_analysis()`
- Chunks on paragraph/sentence boundaries (max 3000 chars)
- Processes chunks in parallel (max 3 concurrent)
- Merges corrections with position adjustment

### TTS Integration

Read-aloud uses `useReadAloud` hook with sentence-level caching:
- Splits text into sentences
- Batch TTS API calls (50 sentences)
- `useTtsPrewarmer` pre-generates audio for changed sentences during idle periods
- Fallback: MagpieTTS → browser Web Speech API

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/WritingModes/PolishMode.tsx` | Main component |
| `frontend/src/components/Panels/CoachPanel.tsx` | AI coach chat |
| `frontend/src/hooks/useReadAloud.ts` | TTS with sentence caching |
| `frontend/src/hooks/useTtsPrewarmer.ts` | Background TTS cache warming |
| `frontend/src/services/ttsSentenceCache.ts` | LRU sentence audio cache |
| `backend/app/core/llm_orchestrator.py` | `document_review()` — always Tier 2 |
| `backend/app/services/nemotron_client.py` | Chunked deep analysis |

## Integration Points

- [Draft Mode](draft-mode.md): Receives completed draft
- [TTS](../backend/text-to-speech.md): MagpieTTS for read-aloud
- [Error Profile](../core/error-profile-system.md): Deep analysis updates profile
- [LLM Orchestrator](../backend/llm-orchestrator.md): Document review endpoint

## Status

- [x] Full-page document view with zoom
- [x] Coach panel integration
- [x] Polish panel with suggestions
- [x] Read-aloud with TTS prewarming
- [x] Sentence-level audio caching
- [ ] Tracked changes UI (accept/dismiss inline)
- [ ] Readability scoring display
- [ ] Session summary
