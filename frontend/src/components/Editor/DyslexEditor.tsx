import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import CharacterCount from '@tiptap/extension-character-count';
import Highlight from '@tiptap/extension-highlight';
import { useEffect, useMemo, useRef } from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import { useEditorStore, Correction } from '../../stores/editorStore';
import { CorrectionHighlightExtension } from './extensions/CorrectionHighlightExtension';
import { FocusModeExtension } from './extensions/FocusModeExtension';
import { TrackedChangesExtension } from './extensions/TrackedChangesExtension';
import { useFrustrationDetector } from '../../hooks/useFrustrationDetector';
import { CheckInPrompt } from './CheckInPrompt';

interface DyslexEditorProps {
  mode?: 'draft' | 'polish';
  onEditorReady?: (editor: Editor) => void;
  onCorrectionClick?: (correction: Correction, rect: DOMRect) => void;
}

export function DyslexEditor({ mode = 'draft', onEditorReady, onCorrectionClick }: DyslexEditorProps) {
  const { font, fontSize, lineSpacing } = useSettingsStore();
  const content = useEditorStore((s) => s.content);
  const setContent = useEditorStore((s) => s.setContent);
  const corrections = useEditorStore((s) => s.corrections);
  const setEditorInstance = useEditorStore((s) => s.setEditorInstance);

  // Use a ref for onCorrectionClick to keep extensions stable across renders
  const correctionClickRef = useRef(onCorrectionClick);
  correctionClickRef.current = onCorrectionClick;

  // Build extensions based on mode
  const extensions = useMemo(() => {
    const baseExtensions = [
      StarterKit,
      Placeholder.configure({
        placeholder: 'Start writing...',
      }),
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      CharacterCount,
      Highlight,
      FocusModeExtension,
    ];

    // Add mode-specific extensions
    if (mode === 'polish') {
      return [...baseExtensions, TrackedChangesExtension];
    } else {
      return [
        ...baseExtensions,
        CorrectionHighlightExtension.configure({
          onCorrectionClick: (...args: [Correction, DOMRect]) => correctionClickRef.current?.(...args),
        }),
      ];
    }
  }, [mode]);

  const editor = useEditor({
    extensions,
    content,
    onUpdate: ({ editor }) => {
      setContent(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'dyslex-editor__content',
      },
    },
  });

  // Update corrections when they change (only in draft mode where CorrectionHighlightExtension is loaded)
  useEffect(() => {
    if (editor && !editor.isDestroyed && corrections && mode !== 'polish') {
      if (typeof editor.commands.setCorrections === 'function') {
        editor.commands.setCorrections(corrections);
      }
    }
  }, [editor, corrections, mode]);

  // Notify parent and store when editor is ready
  useEffect(() => {
    if (editor) {
      setEditorInstance(editor);
      onEditorReady?.(editor);
    }
    return () => {
      setEditorInstance(null);
    };
    // setEditorInstance and onEditorReady are stable references
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor]);

  // Add frustration detector (only in draft mode)
  const {
    shouldShowCheckIn,
    checkInSignals,
    dismissCheckIn,
    handleCheckInAction
  } = useFrustrationDetector(mode === 'draft' ? editor : null);

  // Apply typography settings
  const editorStyle: React.CSSProperties = {
    fontFamily: font,
    fontSize: `${fontSize}px`,
    lineHeight: lineSpacing,
  };

  return (
    <div className="dyslex-editor" style={editorStyle}>
      {/* Check-in prompt appears at top when frustration detected */}
      {shouldShowCheckIn && (
        <CheckInPrompt
          signalTypes={checkInSignals}
          onDismiss={dismissCheckIn}
          onAction={handleCheckInAction}
        />
      )}

      <EditorContent editor={editor} />
    </div>
  );
}
