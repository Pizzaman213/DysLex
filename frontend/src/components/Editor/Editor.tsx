import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Highlight from '@tiptap/extension-highlight';
import { useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';
import { useSnapshotEngine } from '../../hooks/useSnapshotEngine';
import { CorrectionOverlay } from './CorrectionOverlay';

interface EditorProps {
  mode: 'capture' | 'mindmap' | 'draft' | 'polish';
}

export function Editor({ mode }: EditorProps) {
  const { content, setContent, corrections } = useEditorStore();

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
    editorProps: {
      attributes: {
        class: 'dyslex-editor',
        'aria-label': 'Writing editor',
        role: 'textbox',
        'aria-multiline': 'true',
      },
    },
  });

  // Passive learning: auto-snapshots every 5s + pause detection + batched correction logging
  useSnapshotEngine(editor);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Tab' && corrections.length > 0) {
        event.preventDefault();
        // Accept first correction
      }
    },
    [corrections]
  );

  return (
    <div className="editor-wrapper" onKeyDown={handleKeyDown}>
      <EditorContent editor={editor} />
      <CorrectionOverlay editor={editor} corrections={corrections} />
    </div>
  );
}

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
