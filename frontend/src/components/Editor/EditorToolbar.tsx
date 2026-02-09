import { useState, useEffect } from 'react';
import { Editor } from '@tiptap/react';
import { useSettingsStore } from '../../stores/settingsStore';
import { FormatSelector } from './FormatSelector';

interface EditorToolbarProps {
  editor: Editor | null;
  panelsVisible?: boolean;
  onTogglePanels?: () => void;
  onReadAloud?: () => void;
  isReadAloudPlaying?: boolean;
  isReadAloudLoading?: boolean;
  readAloudDisabled?: boolean;
}

export function EditorToolbar({ editor, panelsVisible, onTogglePanels, onReadAloud }: EditorToolbarProps) {
  const { font, setFont, fontSize, setFontSize, zoom, setZoom, showZoom } = useSettingsStore();
  const [sizeInput, setSizeInput] = useState(String(fontSize));

  // Sync local input when fontSize changes externally (e.g. format selector)
  useEffect(() => {
    setSizeInput(String(fontSize));
  }, [fontSize]);

  if (!editor) {
    return null;
  }

  const fonts = [
    'OpenDyslexic',
    'AtkinsonHyperlegible',
    'LexieReadable',
    'TimesNewRoman',
    'Calibri',
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

        <input
          className="editor-toolbar__size-input"
          type="text"
          inputMode="numeric"
          value={sizeInput}
          onChange={(e) => {
            const raw = e.target.value.replace(/[^0-9]/g, '');
            setSizeInput(raw);
          }}
          onBlur={() => {
            const n = parseInt(sizeInput, 10);
            if (!isNaN(n) && n >= 8 && n <= 72) {
              setFontSize(n);
              setSizeInput(String(n));
            } else {
              setSizeInput(String(fontSize));
            }
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              (e.target as HTMLInputElement).blur();
            }
          }}
          aria-label="Font size"
          title="Font size — type a value (8–72)"
        />
      </div>

      {/* Format group */}
      <div className="editor-toolbar__group">
        <FormatSelector />
      </div>

      {/* Zoom group (toggled via Settings > Appearance) */}
      {showZoom && (
        <div className="editor-toolbar__group editor-toolbar__zoom">
          <button
            className="editor-toolbar__btn"
            onClick={() => setZoom(zoom - 10)}
            disabled={zoom <= 25}
            aria-label="Zoom out"
            title="Zoom out"
            type="button"
          >
            <span className="editor-toolbar__icon">−</span>
          </button>

          <span className="editor-toolbar__zoom-label">{zoom}%</span>

          <button
            className="editor-toolbar__btn"
            onClick={() => setZoom(zoom + 10)}
            disabled={zoom >= 200}
            aria-label="Zoom in"
            title="Zoom in"
            type="button"
          >
            <span className="editor-toolbar__icon">+</span>
          </button>
        </div>
      )}

      {/* Read aloud + Toggle panels - pushed to far right */}
      {(onReadAloud || onTogglePanels) && (
        <div className="editor-toolbar__group" style={{ marginLeft: 'auto' }}>

          {onTogglePanels && (
            <button
              className={`editor-toolbar__btn ${panelsVisible ? 'is-active' : ''}`}
              onClick={onTogglePanels}
              aria-label={panelsVisible ? 'Hide panels' : 'Show panels'}
              aria-pressed={panelsVisible}
              title={panelsVisible ? 'Hide scaffold & suggestions' : 'Show scaffold & suggestions'}
              type="button"
            >
              <span className="editor-toolbar__icon">
                {panelsVisible ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                )}
              </span>
              <span className="editor-toolbar__label">Panels</span>
            </button>
          )}
        </div>
      )}

    </div>
  );
}
