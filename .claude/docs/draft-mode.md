# Draft Mode — Scaffolded Writing

## Purpose

Draft Mode is where actual writing happens. It provides a scaffolded structure (from Mind Map) with inline corrections and AI coaching — all while passive learning runs silently in the background.

**Key insight**: Give structure without forcing it. Corrections without interruption. Help without condescension.

## User Experience

### Three-Column Layout

1. **Left: Essay Scaffold**
   - Section headers (Introduction, Main Points, Conclusion)
   - Progress indicators for each section
   - Collapsible sections

2. **Center: Main Editor**
   - TipTap rich text editor
   - Inline corrections (subtle underlines, not red)
   - AI coach nudges (gentle prompts, easy to dismiss)
   - Full writing toolbar

3. **Right: Corrections Panel**
   - List of suggested corrections
   - Explanations for each
   - One-click apply (optional)

### What Users See
- Clean writing canvas
- Subtle correction indicators
- Encouraging progress tracking
- Easy navigation between sections

### What Users Don't See
- Passive learning happening
- Error profile updates
- LLM calls being made
- Snapshot diffing

## Technical Implementation

### Main Editor Component

```typescript
// frontend/src/components/Editor/Editor.tsx
export function Editor({ mode }: EditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: getPlaceholder(mode) }),
      Highlight.configure({ multicolor: true }),
    ],
    onUpdate: ({ editor }) => setContent(editor.getHTML()),
    onBlur: () => computeDiff(),
  });

  // Snapshot every 5-10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (editor) takeSnapshot(editor.getText());
    }, 5000);
    return () => clearInterval(interval);
  }, [editor, takeSnapshot]);

  return (
    <div className="editor-wrapper">
      <EditorContent editor={editor} />
      <CorrectionOverlay editor={editor} corrections={corrections} />
    </div>
  );
}
```

### Correction Overlay

```typescript
// frontend/src/components/Editor/CorrectionOverlay.tsx
export function CorrectionOverlay({ editor, corrections }) {
  // Positions correction markers at exact text locations
  // Shows subtle underlines (not aggressive red)
  // Clicking shows suggestion + explanation
  // Never blocks typing flow
}
```

### Draft Mode Wrapper

```typescript
// frontend/src/components/WritingModes/DraftMode.tsx
export function DraftMode({ initialContent }: DraftModeProps) {
  return (
    <div className="draft-mode">
      <div className="draft-scaffold">
        <ScaffoldSection title="Introduction" hint="What are you writing about?" />
        <ScaffoldSection title="Main Points" hint="What are your key ideas?" />
        <ScaffoldSection title="Conclusion" hint="How will you wrap up?" />
      </div>
      <Editor mode="draft" />
    </div>
  );
}
```

## Correction Display

### Underline Styles
- **Spelling**: Soft coral underline
- **Grammar**: Soft blue underline
- **Homophone**: Soft orange underline
- **Phonetic**: Soft green underline

### Correction Card
```
┌─────────────────────────────────┐
│ "becuase" → "because"           │
│                                 │
│ The letters got mixed up.       │
│ This happens with longer words! │
└─────────────────────────────────┘
```

- Never says "error" or "mistake"
- Uses encouraging, normalizing language
- Short, clear explanations

## Key Files

### Frontend
- `frontend/src/components/Editor/Editor.tsx` — TipTap wrapper
- `frontend/src/components/Editor/CorrectionOverlay.tsx` — Correction display
- `frontend/src/components/Editor/Toolbar.tsx` — Formatting toolbar
- `frontend/src/components/WritingModes/DraftMode.tsx` — Mode wrapper
- `frontend/src/components/Panels/CorrectionsPanel.tsx` — Side panel

### Backend
- `backend/app/api/routes/corrections.py` — Correction API
- `backend/app/core/llm_orchestrator.py` — LLM routing

## Passive Learning Integration

While user writes:
1. `usePassiveLearning` takes snapshots
2. Diffs computed on pause
3. Self-corrections detected
4. Error Profile updated in background
5. Future corrections improve automatically

## AI Coach Nudges (Future)

Gentle prompts that appear when appropriate:
- "You've been on this paragraph a while. Want to talk through it?"
- "Great progress! You've written 200 words this session."
- "This section is getting long. Maybe break it up?"

Rules:
- Never interrupt flow
- Easy to dismiss
- Never condescending
- Optional to enable

## Accessibility Requirements

- **Keyboard shortcuts**: All formatting accessible
- **Screen reader**: Corrections announced appropriately
- **Focus management**: Never lose cursor position
- **Visible focus**: Clear indication of current position
- **Customizable**: User controls correction visibility

## Integration Points

- **Mind Map Mode**: Receives scaffold structure
- **Polish Mode**: Sends draft for review
- **Error Profile**: Sends behavioral data
- **Quick Correction Model**: Provides instant fixes

## Status

- [x] TipTap editor integrated
- [x] Basic correction overlay
- [x] Toolbar implemented
- [x] Passive learning hooks
- [ ] Full scaffold UI
- [ ] AI coach nudges
- [ ] Section progress tracking
