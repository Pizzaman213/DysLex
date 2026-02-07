import { Editor } from '@tiptap/react';
import { useSettingsStore } from '../../stores/settingsStore';
import { ExportMenu } from './ExportMenu';

interface EditorToolbarProps {
  editor: Editor | null;
}

export function EditorToolbar({ editor }: EditorToolbarProps) {
  const { font, setFont, focusMode, setFocusMode } = useSettingsStore();

  if (!editor) {
    return null;
  }

  const fonts = [
    'OpenDyslexic',
    'AtkinsonHyperlegible',
    'LexieReadable',
    'system',
  ];

  return (
    <div className="editor-toolbar" role="toolbar" aria-label="Text formatting">
      {/* Format group */}
      <div className="editor-toolbar__group">
        <button
          className={`editor-toolbar__btn ${editor.isActive('bold') ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleBold().run()}
          aria-label="Bold"
          aria-pressed={editor.isActive('bold')}
          title="Bold (Ctrl+B)"
          type="button"
        >
          <span className="editor-toolbar__icon">B</span>
          <span className="editor-toolbar__label">Bold</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive('italic') ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          aria-label="Italic"
          aria-pressed={editor.isActive('italic')}
          title="Italic (Ctrl+I)"
          type="button"
        >
          <span className="editor-toolbar__icon">I</span>
          <span className="editor-toolbar__label">Italic</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive('underline') ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          aria-label="Underline"
          aria-pressed={editor.isActive('underline')}
          title="Underline (Ctrl+U)"
          type="button"
        >
          <span className="editor-toolbar__icon">U</span>
          <span className="editor-toolbar__label">Underline</span>
        </button>
      </div>

      {/* Headings group */}
      <div className="editor-toolbar__group">
        <button
          className={`editor-toolbar__btn ${editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          aria-label="Heading 1"
          aria-pressed={editor.isActive('heading', { level: 1 })}
          title="Heading 1"
          type="button"
        >
          <span className="editor-toolbar__icon">H1</span>
          <span className="editor-toolbar__label">Heading 1</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          aria-label="Heading 2"
          aria-pressed={editor.isActive('heading', { level: 2 })}
          title="Heading 2"
          type="button"
        >
          <span className="editor-toolbar__icon">H2</span>
          <span className="editor-toolbar__label">Heading 2</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive('heading', { level: 3 }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          aria-label="Heading 3"
          aria-pressed={editor.isActive('heading', { level: 3 })}
          title="Heading 3"
          type="button"
        >
          <span className="editor-toolbar__icon">H3</span>
          <span className="editor-toolbar__label">Heading 3</span>
        </button>
      </div>

      {/* Lists group */}
      <div className="editor-toolbar__group">
        <button
          className={`editor-toolbar__btn ${editor.isActive('bulletList') ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          aria-label="Bullet list"
          aria-pressed={editor.isActive('bulletList')}
          title="Bullet list"
          type="button"
        >
          <span className="editor-toolbar__icon">•</span>
          <span className="editor-toolbar__label">Bullet</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive('orderedList') ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          aria-label="Numbered list"
          aria-pressed={editor.isActive('orderedList')}
          title="Numbered list"
          type="button"
        >
          <span className="editor-toolbar__icon">1.</span>
          <span className="editor-toolbar__label">Numbered</span>
        </button>
      </div>

      {/* Alignment group */}
      <div className="editor-toolbar__group">
        <button
          className={`editor-toolbar__btn ${editor.isActive({ textAlign: 'left' }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          aria-label="Align left"
          aria-pressed={editor.isActive({ textAlign: 'left' })}
          title="Align left"
          type="button"
        >
          <span className="editor-toolbar__icon">⬅</span>
          <span className="editor-toolbar__label">Left</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive({ textAlign: 'center' }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          aria-label="Align center"
          aria-pressed={editor.isActive({ textAlign: 'center' })}
          title="Align center"
          type="button"
        >
          <span className="editor-toolbar__icon">↔</span>
          <span className="editor-toolbar__label">Center</span>
        </button>

        <button
          className={`editor-toolbar__btn ${editor.isActive({ textAlign: 'right' }) ? 'is-active' : ''}`}
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          aria-label="Align right"
          aria-pressed={editor.isActive({ textAlign: 'right' })}
          title="Align right"
          type="button"
        >
          <span className="editor-toolbar__icon">➡</span>
          <span className="editor-toolbar__label">Right</span>
        </button>
      </div>

      {/* History group */}
      <div className="editor-toolbar__group">
        <button
          className="editor-toolbar__btn"
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
          aria-label="Undo"
          title="Undo (Ctrl+Z)"
          type="button"
        >
          <span className="editor-toolbar__icon">↶</span>
          <span className="editor-toolbar__label">Undo</span>
        </button>

        <button
          className="editor-toolbar__btn"
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
          aria-label="Redo"
          title="Redo (Ctrl+Y)"
          type="button"
        >
          <span className="editor-toolbar__icon">↷</span>
          <span className="editor-toolbar__label">Redo</span>
        </button>
      </div>

      {/* Tools group */}
      <div className="editor-toolbar__group">
        <select
          className="editor-toolbar__select"
          value={font}
          onChange={(e) => setFont(e.target.value as any)}
          aria-label="Select font"
        >
          {fonts.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      {/* Export group */}
      <div className="editor-toolbar__group">
        <ExportMenu editor={editor} />
      </div>

      {/* Focus mode - pushed to far right */}
      <div className="editor-toolbar__group" style={{ marginLeft: 'auto' }}>
        <button
          className={`editor-toolbar__btn ${focusMode ? 'is-active' : ''}`}
          onClick={() => {
            const newFocusMode = !focusMode;
            setFocusMode(newFocusMode);
            editor.commands.setFocusMode(newFocusMode);
          }}
          aria-label="Focus mode"
          aria-pressed={focusMode}
          title="Focus mode - dim other paragraphs"
          type="button"
        >
          <span className="editor-toolbar__icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></span>
          <span className="editor-toolbar__label">Focus</span>
        </button>
      </div>

    </div>
  );
}
