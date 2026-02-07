import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as PMNode } from '@tiptap/pm/model';
import { Correction } from '../../../stores/editorStore';

export interface CorrectionHighlightOptions {
  onCorrectionClick: (correction: Correction, rect: DOMRect) => void;
}

export const CorrectionHighlightExtension = Extension.create<CorrectionHighlightOptions>({
  name: 'correctionHighlight',

  addOptions() {
    return {
      onCorrectionClick: () => {},
    };
  },

  addProseMirrorPlugins() {
    const extensionThis = this;

    return [
      new Plugin({
        key: new PluginKey('correctionHighlight'),
        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, set) {
            // Get corrections from transaction metadata
            const corrections = tr.getMeta('corrections');
            if (corrections !== undefined) {
              return createDecorations(corrections, tr.doc, extensionThis.options.onCorrectionClick);
            }
            // Map existing decorations through document changes
            return set.map(tr.mapping, tr.doc);
          },
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
        },
      }),
    ];
  },

  addCommands() {
    return {
      setCorrections:
        (corrections: Correction[]) =>
        ({ tr, dispatch }: any) => {
          if (dispatch) {
            tr.setMeta('corrections', corrections);
          }
          return true;
        },
    } as any;
  },
});

function createDecorations(
  corrections: Correction[],
  doc: PMNode,
  onCorrectionClick: (correction: Correction, rect: DOMRect) => void
): DecorationSet {
  const decorations: Decoration[] = [];

  corrections.forEach((correction) => {
    if (correction.isApplied || correction.isDismissed) {
      return; // Skip applied/dismissed corrections
    }

    // Ensure positions are within document bounds
    if (correction.start < 0 || correction.end > doc.content.size) {
      return;
    }

    const decoration = Decoration.inline(
      correction.start,
      correction.end,
      {
        class: `correction-underline correction-underline-${correction.type}`,
        'data-correction-id': correction.id,
      },
      {
        correction,
        onCorrectionClick,
      }
    );

    decorations.push(decoration);
  });

  return DecorationSet.create(doc, decorations);
}

// Add global click handler for correction underlines
if (typeof document !== 'undefined') {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const correctionEl = target.closest('.correction-underline');

    if (correctionEl) {
      const correctionId = correctionEl.getAttribute('data-correction-id');
      if (correctionId) {
        const rect = correctionEl.getBoundingClientRect();
        // Dispatch custom event that DyslexEditor will listen for
        const event = new CustomEvent('correction-click', {
          detail: { correctionId, rect },
        });
        document.dispatchEvent(event);
      }
    }
  });
}
