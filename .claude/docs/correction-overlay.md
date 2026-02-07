# Correction Overlay

## Purpose

The Correction Overlay displays inline corrections without interrupting the writing flow. Corrections appear as subtle underlines — not aggressive red marks or intrusive popups.

**Key insight**: The best corrections are the ones that don't break concentration.

## User Experience

### What Users See
- Subtle colored underlines beneath words with suggestions
- Clicking a word shows the suggestion + explanation
- Tab key accepts the first suggestion (optional)
- No modal dialogs, no popups blocking the view

### What Users Don't See
- Complex positioning calculations
- Confidence scores
- Technical error classifications

## Visual Design

### Underline Colors (Subtle, Not Aggressive)

| Error Type | Cream Theme | Night Theme |
|------------|-------------|-------------|
| Spelling | Soft coral (#f5d4d4) | Muted red (#4a3535) |
| Grammar | Soft blue (#d4e4f5) | Muted blue (#35454a) |
| Confusion | Soft orange (#f5e4d4) | Muted orange (#4a4535) |
| Phonetic | Soft green (#e4f5d4) | Muted green (#3a4a35) |

### Correction Card (On Click)

```
┌─────────────────────────────────────┐
│ becuase → because                   │
│                                     │
│ The letters got mixed up.           │
│ This is really common!              │
└─────────────────────────────────────┘
```

- Shows original and suggestion
- Friendly, normalizing explanation
- Never says "error" or "mistake"

## Technical Implementation

### Overlay Component

```typescript
// frontend/src/components/Editor/CorrectionOverlay.tsx
interface CorrectionOverlayProps {
  editor: Editor | null;
  corrections: Correction[];
}

export function CorrectionOverlay({ editor, corrections }: CorrectionOverlayProps) {
  if (!editor || corrections.length === 0) {
    return null;
  }

  return (
    <div className="correction-overlay" aria-live="polite">
      {corrections.map((correction) => (
        <CorrectionMarker
          key={`${correction.start}-${correction.end}`}
          correction={correction}
          editor={editor}
        />
      ))}
    </div>
  );
}
```

### Correction Marker

```typescript
interface CorrectionMarkerProps {
  correction: Correction;
  editor: Editor;
}

function CorrectionMarker({ correction, editor }: CorrectionMarkerProps) {
  const [showCard, setShowCard] = useState(false);
  const position = calculatePosition(editor, correction.start, correction.end);

  return (
    <div
      className={`correction-marker correction-${correction.type}`}
      style={{ left: position.x, top: position.y, width: position.width }}
      onClick={() => setShowCard(!showCard)}
      role="button"
      tabIndex={0}
      aria-label={`Suggestion: replace "${correction.original}" with "${correction.suggested}"`}
    >
      {showCard && (
        <CorrectionCard
          original={correction.original}
          suggested={correction.suggested}
          explanation={correction.explanation}
          onApply={() => applyCorrection(editor, correction)}
          onDismiss={() => setShowCard(false)}
        />
      )}
    </div>
  );
}
```

### Position Calculation

```typescript
function calculatePosition(editor: Editor, start: number, end: number) {
  // Get the DOM coordinates for the text range
  const view = editor.view;
  const startCoords = view.coordsAtPos(start);
  const endCoords = view.coordsAtPos(end);

  return {
    x: startCoords.left,
    y: startCoords.bottom,
    width: endCoords.right - startCoords.left,
  };
}
```

### Correction Card Component

```typescript
function CorrectionCard({ original, suggested, explanation, onApply, onDismiss }) {
  return (
    <div className="correction-card" role="dialog" aria-label="Correction suggestion">
      <div className="correction-content">
        <span className="correction-original">{original}</span>
        <span className="correction-arrow" aria-hidden="true">→</span>
        <span className="correction-suggested">{suggested}</span>
      </div>
      {explanation && (
        <p className="correction-explanation">{explanation}</p>
      )}
      <div className="correction-actions">
        <button onClick={onApply} aria-label="Apply correction">
          Apply
        </button>
        <button onClick={onDismiss} aria-label="Dismiss">
          Dismiss
        </button>
      </div>
    </div>
  );
}
```

## Applying Corrections

```typescript
function applyCorrection(editor: Editor, correction: Correction) {
  editor
    .chain()
    .focus()
    .setTextSelection({ from: correction.start, to: correction.end })
    .insertContent(correction.suggested)
    .run();

  // Note: This triggers the passive learning loop
  // The correction is detected as "applied" and logged
}
```

## Key Files

- `frontend/src/components/Editor/CorrectionOverlay.tsx`
- `frontend/src/components/Editor/CorrectionMarker.tsx` (future)
- `frontend/src/components/Editor/CorrectionCard.tsx` (future)

## Accessibility

- **Keyboard navigation**: Tab to navigate corrections
- **Screen reader**: Each correction announced with context
- **No time pressure**: Corrections persist until addressed
- **Escape to dismiss**: Easy way to hide cards
- **Focus management**: Focus returns to editor after apply

## CSS Styling

```css
.correction-marker {
  position: absolute;
  border-bottom: 2px solid;
  cursor: pointer;
  pointer-events: auto;
}

.correction-spelling { border-color: var(--color-correction-spelling); }
.correction-grammar { border-color: var(--color-correction-grammar); }
.correction-confusion { border-color: var(--color-correction-confusion); }
.correction-phonetic { border-color: var(--color-correction-phonetic); }

.correction-card {
  position: absolute;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  box-shadow: var(--shadow-lg);
  z-index: 100;
}
```

## Integration Points

- **Editor**: Provides text positions
- **Correction Service**: Provides correction data
- **Error Profile**: Logs when corrections are applied
- **Passive Learning**: Detects if user applies or ignores

## Performance

- Only render visible corrections
- Debounce position recalculation on scroll
- Lazy load correction cards
- Limit to ~20 visible markers

## Status

- [x] Basic overlay structure
- [x] Marker positioning concept
- [ ] Full TipTap integration
- [ ] Correction card UI
- [ ] Apply/dismiss functionality
- [ ] Keyboard navigation
- [ ] Performance optimization
