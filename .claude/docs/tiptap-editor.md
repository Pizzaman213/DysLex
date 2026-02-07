# TipTap Editor

## Purpose

TipTap is the core rich text editor powering DysLex AI. Built on ProseMirror, it provides a solid foundation for the correction overlay, passive learning snapshots, and accessibility features.

**Why TipTap**: Modular, extensible, accessible by default, great React integration.

## User Experience

Users interact with a clean, distraction-free writing surface:
- Standard formatting (bold, italic, headings, lists)
- Inline corrections that don't interrupt typing
- Keyboard shortcuts that match familiar editors
- Focus mode that dims distractions

## Technical Implementation

### Editor Setup

```typescript
// frontend/src/components/Editor/Editor.tsx
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Highlight from '@tiptap/extension-highlight';

export function Editor({ mode }: EditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: getPlaceholder(mode),
      }),
      Highlight.configure({
        multicolor: true,
      }),
    ],
    content,
    onUpdate: ({ editor }) => {
      setContent(editor.getHTML());
    },
    onBlur: () => {
      computeDiff();  // Trigger passive learning
    },
    editorProps: {
      attributes: {
        class: 'dyslex-editor',
        'aria-label': 'Writing editor',
        role: 'textbox',
        'aria-multiline': 'true',
      },
    },
  });

  return (
    <div className="editor-wrapper">
      <EditorContent editor={editor} />
      <CorrectionOverlay editor={editor} corrections={corrections} />
    </div>
  );
}
```

### Extensions Used

| Extension | Purpose |
|-----------|---------|
| StarterKit | Basic formatting (bold, italic, lists, headings) |
| Placeholder | Mode-specific placeholder text |
| Highlight | Multicolor highlighting for corrections |
| (Future) CorrectionMark | Custom marks for error underlining |
| (Future) FocusMode | Dims non-active paragraphs |

### Custom Extensions (Planned)

```typescript
// Correction decoration extension
export const CorrectionHighlight = Extension.create({
  name: 'correctionHighlight',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('correctionHighlight'),
        props: {
          decorations: (state) => {
            // Create decorations for each correction
            // Position at exact character offsets
            // Style based on correction type
          },
        },
      }),
    ];
  },
});
```

## Toolbar Implementation

```typescript
// frontend/src/components/Editor/Toolbar.tsx
export function Toolbar({ mode }: ToolbarProps) {
  return (
    <div className="toolbar" role="toolbar" aria-label="Editor toolbar">
      {mode === 'capture' && <VoiceBar />}

      {(mode === 'draft' || mode === 'polish') && (
        <div className="format-tools">
          <button aria-label="Bold" title="Bold (Ctrl+B)">B</button>
          <button aria-label="Italic" title="Italic (Ctrl+I)">I</button>
          <button aria-label="Heading" title="Heading">H</button>
          <button aria-label="List" title="Bullet list">•</button>
        </div>
      )}

      {mode === 'polish' && (
        <div className="polish-tools">
          <button aria-label="Read aloud">🔊</button>
          <button aria-label="Check grammar">✓</button>
        </div>
      )}
    </div>
  );
}
```

## Key Files

- `frontend/src/components/Editor/Editor.tsx` — Main editor
- `frontend/src/components/Editor/Toolbar.tsx` — Formatting toolbar
- `frontend/src/components/Editor/CorrectionOverlay.tsx` — Correction display
- `frontend/src/components/Editor/plugins/` — Custom TipTap extensions

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+B | Bold |
| Ctrl+I | Italic |
| Ctrl+U | Underline |
| Ctrl+Shift+1-6 | Headings |
| Ctrl+Shift+8 | Bullet list |
| Ctrl+Shift+9 | Numbered list |
| Tab | Accept first correction (custom) |
| Escape | Dismiss corrections (custom) |

## Placeholder Text by Mode

```typescript
function getPlaceholder(mode: string): string {
  switch (mode) {
    case 'capture':
      return 'Speak or type your thoughts freely...';
    case 'mindmap':
      return 'Organize your ideas visually...';
    case 'draft':
      return 'Start writing your draft...';
    case 'polish':
      return 'Review and refine your work...';
    default:
      return 'Start writing...';
  }
}
```

## Accessibility Requirements

- **ARIA roles**: `textbox` with `aria-multiline`
- **Keyboard access**: All formatting via keyboard
- **Focus visible**: Clear focus ring
- **Screen reader**: Content changes announced
- **High contrast**: Works in all themes

## Integration Points

- **Passive Learning**: Snapshots taken on change
- **Correction Service**: Text sent for analysis
- **Correction Overlay**: Displays inline suggestions
- **Error Profile**: Behavioral data captured

## Performance Considerations

- Debounce API calls (don't send on every keystroke)
- Virtualize long documents
- Lazy load unused extensions
- Use React.memo for stable components

## Status

- [x] Basic TipTap setup
- [x] StarterKit integrated
- [x] Placeholder extension
- [x] Toolbar component
- [ ] Custom correction extension
- [ ] Focus mode extension
- [ ] Full keyboard shortcuts
