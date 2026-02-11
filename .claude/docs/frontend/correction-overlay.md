# Correction Overlay

## Purpose

Displays inline corrections without interrupting writing flow. Corrections appear as subtle colored underlines — not aggressive red marks or intrusive popups.

## Current Implementation

Corrections are rendered in two places:

### 1. Inline Underlines (DraftMode)

In `DraftMode.tsx`, corrections are mapped to ProseMirror positions and rendered as TipTap decorations:
- Position mapping converts plain-text offsets to ProseMirror document positions
- Content-based correction IDs ensure stable state across re-renders
- 800ms debounce prevents excessive API calls
- Underline color varies by error type

### 2. CorrectionOverlay Component

`frontend/src/components/Editor/CorrectionOverlay.tsx`:
- Renders a list of correction divs with original → suggested display
- Aria-live region for screen reader announcements
- Keyboard accessible (tabindex, role="button")
- Shows explanation text if available

### Correction Tooltip

On underline click in DraftMode, a tooltip appears showing:
- Original text → suggested replacement
- Friendly explanation (never says "error" or "mistake")
- Apply/dismiss buttons

## Underline Colors

| Error Type | Cream Theme | Night Theme |
|------------|-------------|-------------|
| Spelling | Soft coral (#f5d4d4) | Muted red (#4a3535) |
| Grammar | Soft blue (#d4e4f5) | Muted blue (#35454a) |
| Confusion | Soft orange (#f5e4d4) | Muted orange (#4a4535) |
| Phonetic | Soft green (#e4f5d4) | Muted green (#3a4a35) |

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/Editor/CorrectionOverlay.tsx` | Correction decoration layer |
| `frontend/src/components/WritingModes/DraftMode.tsx` | Inline underline rendering |
| `frontend/src/components/Panels/CorrectionsPanel.tsx` | Side panel with all corrections |
| `frontend/src/styles/global.css` | Correction color tokens |

## Integration Points

- [TipTap Editor](tiptap-editor.md): Provides text positions and decorations
- [ONNX Correction](onnx-local-correction.md): Source of correction data
- [LLM Orchestrator](../backend/llm-orchestrator.md): Backend correction source
- [Adaptive Loop](../core/adaptive-learning-loop.md): Logs applied/ignored corrections

## Status

- [x] Inline underlines via TipTap decorations
- [x] Correction tooltip on click
- [x] CorrectionsPanel with apply/dismiss/explain
- [x] Color-coded by error type
- [x] Accessible (aria-live, keyboard nav)
- [ ] Custom TipTap CorrectionMark extension
- [ ] Tab key to accept first correction
