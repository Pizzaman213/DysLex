import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Highlight from '@tiptap/extension-highlight';
import { useEffect, useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';
import { usePassiveLearning } from '../../hooks/usePassiveLearning';
import { CorrectionOverlay } from './CorrectionOverlay';

interface EditorProps {
  mode: 'capture' | 'mindmap' | 'draft' | 'polish';
}

export function Editor({ mode }: EditorProps) {
  const { content, setContent, corrections } = useEditorStore();
  const { takeSnapshot, computeDiff } = usePassiveLearning();

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
      computeDiff();
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

  useEffect(() => {
    const interval = setInterval(() => {
      if (editor) {
        takeSnapshot(editor.getText());
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [editor, takeSnapshot]);

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
