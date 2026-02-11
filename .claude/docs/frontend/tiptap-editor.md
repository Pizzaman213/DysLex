# TipTap Editor

## Purpose

TipTap (ProseMirror-based) is the core rich text editor. Two editor components exist: a simple `Editor.tsx` wrapper and the full-featured `DyslexEditor.tsx` used in Draft and Polish modes.

## Editor Components

### Editor.tsx (Simple)

`frontend/src/components/Editor/Editor.tsx`:
- StarterKit + Placeholder + Highlight extensions
- Mode-specific placeholders (capture/mindmap/draft/polish)
- Basic correction overlay integration

### DyslexEditor.tsx (Full-Featured)

Used by DraftMode and PolishMode. The actual main editor component with:
- Inline correction decorations (underlines by error type)
- Position mapping from plain text offsets to ProseMirror positions
- Correction tooltip popup on click
- Snapshot engine integration for passive learning
- Right-click context menu ("Add to dictionary")
- Page number toggle on margin double-click

### CorrectionOverlay.tsx

`frontend/src/components/Editor/CorrectionOverlay.tsx`:
- Renders correction markers as a decoration layer
- Aria-live region for screen readers
- Keyboard accessible (tabindex, role="button")
- Shows original → suggested with explanation

## Corrections Panel

`frontend/src/components/Panels/CorrectionsPanel.tsx`:
- Lists all active corrections with apply/dismiss/explain buttons
- Sorts by document position
- "Apply All" bulk action
- Click scrolls editor to correction location
- Hover-to-highlight state
- Color-coded badges by error type (Omission, Insertion, Transposition, etc.)
- "Why?" button sends correction to AI coach for explanation

## AI Coach Panel

`frontend/src/components/Panels/CoachPanel.tsx`:
- Chat interface for AI writing coach
- Welcome state with suggested starter questions
- Auto-scroll to latest message
- Enter-to-send, Shift+Enter for newline
- Auto-sends when correction explanation requested from CorrectionsPanel

Starter prompts:
- "How's my writing going?"
- "Help me get unstuck"
- "What should I work on next?"
- "Can you explain a correction?"

### Coach Store

`frontend/src/stores/coachStore.ts` (Zustand, in-memory only):
- Per-document session management
- `pendingExplainCorrection` — Triggers auto-explanation
- Subscribes to `documentStore` for cleanup

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/Editor/Editor.tsx` | Simple TipTap wrapper |
| `frontend/src/components/WritingModes/DraftMode.tsx` | Contains DyslexEditor |
| `frontend/src/components/Editor/CorrectionOverlay.tsx` | Correction decoration layer |
| `frontend/src/components/Panels/CorrectionsPanel.tsx` | Corrections list panel |
| `frontend/src/components/Panels/CoachPanel.tsx` | AI coach chat |
| `frontend/src/components/Panels/RightPanel.tsx` | Panel switcher |
| `frontend/src/stores/coachStore.ts` | Coach message state |
| `frontend/src/hooks/useCoachChat.ts` | Coach API hook |

## Integration Points

- [Draft Mode](../modes/draft-mode.md): Primary editor consumer
- [Polish Mode](../modes/polish-mode.md): Read-only/review consumer
- [Adaptive Loop](../core/adaptive-learning-loop.md): Snapshot engine
- [ONNX Correction](onnx-local-correction.md): Browser-based corrections

## Status

- [x] TipTap with StarterKit, Placeholder, Highlight
- [x] DyslexEditor with inline correction underlines
- [x] Correction tooltip popup
- [x] CorrectionsPanel with apply/dismiss/explain
- [x] CoachPanel with chat interface
- [x] Per-document coach sessions
- [ ] Custom CorrectionMark TipTap extension
- [ ] Focus mode extension (dim non-active paragraphs)
