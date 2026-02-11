# Draft Mode — Scaffolded Writing

## Purpose

Where actual writing happens. Three-column layout with scaffold, editor with inline corrections, and corrections/coach panel. Passive learning runs silently in background.

## User Experience

### Three-Column Layout

1. **Left: Scaffold Panel** — Section headers from mind map, progress indicators
2. **Center: DyslexEditor** — TipTap rich text with inline correction underlines
3. **Right: Corrections/Coach Panel** — Switchable between corrections list and AI coach

## Technical Implementation

### Main Component

`frontend/src/components/WritingModes/DraftMode.tsx`:
- TipTap editor (`DyslexEditor`) with inline correction decorations
- 800ms debounced correction fetching via `getCorrections()`
- Position mapping from plain text offsets to ProseMirror positions
- Content-based correction IDs for stable state across re-renders
- Correction tooltip popup on underline click
- Voice input for text insertion
- Read-aloud functionality
- Right-click context menu for "Add to dictionary"
- Page number toggle on margin double-click

### Correction Pipeline

1. Editor text changes (debounced 800ms)
2. `loadModel()` initializes ONNX model if needed
3. `getCorrections(text)` calls backend orchestrator
4. Corrections mapped to ProseMirror positions
5. Inline underlines rendered as TipTap decorations
6. Click on underline shows tooltip with suggestion + explanation

### Passive Learning

`useSnapshotEngine` takes periodic text snapshots → sent to backend → `adaptive_loop.py` detects self-corrections → `ErrorProfileService.log_error()` updates profile.

### AI Coach

`useAICoach` hook integrates the AI writing coach. See [CoachPanel](../frontend/tiptap-editor.md) for details. Coach can explain individual corrections when user clicks "Why?" in the corrections panel.

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/WritingModes/DraftMode.tsx` | Main component |
| `frontend/src/components/Panels/CorrectionsPanel.tsx` | Corrections list panel |
| `frontend/src/components/Panels/CoachPanel.tsx` | AI coach chat panel |
| `frontend/src/components/Panels/RightPanel.tsx` | Panel switcher |
| `frontend/src/services/onnxModel.ts` | Local ONNX corrections |
| `frontend/src/stores/coachStore.ts` | Coach message state |
| `backend/app/core/llm_orchestrator.py` | Two-tier correction routing |

## Integration Points

- [Mind Map Mode](mindmap-mode.md): Receives scaffold structure
- [Polish Mode](polish-mode.md): Sends completed draft
- [Adaptive Loop](../core/adaptive-learning-loop.md): Snapshot engine runs in background
- [ONNX Local Correction](../frontend/onnx-local-correction.md): Browser-based spell check
- [Error Profile](../core/error-profile-system.md): Updates from passive learning

## Status

- [x] TipTap editor with inline correction underlines
- [x] 800ms debounced correction fetching
- [x] Corrections panel with apply/dismiss/explain
- [x] AI coach panel with chat interface
- [x] Voice input integration
- [x] Read-aloud integration
- [x] Passive snapshot engine
- [x] Right-click "Add to dictionary"
- [ ] Full scaffold UI with section progress
- [ ] Frustration detection check-in prompts
