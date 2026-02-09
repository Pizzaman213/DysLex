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
import { useDocumentStore } from '../../stores/documentStore';
import { CorrectionHighlightExtension } from './extensions/CorrectionHighlightExtension';
import { FocusModeExtension } from './extensions/FocusModeExtension';
import { TrackedChangesExtension } from './extensions/TrackedChangesExtension';
import { PageBreakExtension } from './extensions/PageBreakExtension';
import { ParagraphIndentExtension } from './extensions/ParagraphIndentExtension';
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
  const activeDocumentId = useDocumentStore((s) => s.activeDocumentId);
  const documents = useDocumentStore((s) => s.documents);

  // Use a ref for onCorrectionClick to keep extensions stable across renders
  const correctionClickRef = useRef(onCorrectionClick);
  correctionClickRef.current = onCorrectionClick;

  // Build extensions based on mode
  const extensions = useMemo(() => {
    const baseExtensions = [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
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
      PageBreakExtension,
      ParagraphIndentExtension,
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
      const html = editor.getHTML();
      setContent(html);
      // cs: persist to documentStore so content survives logout/rehydration
      const docId = useDocumentStore.getState().activeDocumentId;
      if (docId) {
        useDocumentStore.getState().updateDocumentContent(docId, html);
      }
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

  // Sync document content into TipTap when the active document changes.
  // Needed after adding user-scoped storage — c.secrist, 2/9/26
  const prevDocIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (!editor || !activeDocumentId) return;
    const doc = documents.find((d) => d.id === activeDocumentId);
    if (!doc) return;

    // Save current editor content back to the previous document before switching
    if (prevDocIdRef.current && prevDocIdRef.current !== activeDocumentId) {
      const html = editor.getHTML();
      useDocumentStore.getState().updateDocumentContent(prevDocIdRef.current, html);
    }

    // Load the new document's content into the editor
    if (prevDocIdRef.current !== activeDocumentId || (!content && doc.content)) {
      const docContent = doc.content || '';
      if (editor.getHTML() !== docContent) {
        editor.commands.setContent(docContent, false);
        setContent(docContent);
      }
    }

    prevDocIdRef.current = activeDocumentId;
  }, [editor, activeDocumentId, documents, content, setContent]);

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
