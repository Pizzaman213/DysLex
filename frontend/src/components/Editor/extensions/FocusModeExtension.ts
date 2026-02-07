import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export const FocusModeExtension = Extension.create({
  name: 'focusMode',

  addStorage() {
    return {
      enabled: false,
    };
  },

  addProseMirrorPlugins() {
    const extensionThis = this;

    return [
      new Plugin({
        key: new PluginKey('focusMode'),
        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, _set) {
            const enabled = tr.getMeta('focusModeEnabled');
            if (enabled !== undefined) {
              extensionThis.storage.enabled = enabled;
              if (!enabled) {
                return DecorationSet.empty;
              }
            }

            if (!extensionThis.storage.enabled) {
              return DecorationSet.empty;
            }

            // Create decorations for all blocks except the one with cursor
            const { selection, doc } = tr;
            const decorations: Decoration[] = [];

            doc.descendants((node, pos) => {
              // Only process block nodes
              if (!node.isBlock) {
                return;
              }

              // Check if cursor is in this block
              const nodeStart = pos;
              const nodeEnd = pos + node.nodeSize;
              const cursorInBlock =
                selection.from >= nodeStart && selection.to <= nodeEnd;

              if (!cursorInBlock) {
                // Add dimming class to blocks without cursor
                decorations.push(
                  Decoration.node(pos, nodeEnd, {
                    class: 'editor-paragraph--dimmed',
                  })
                );
              }
            });

            return DecorationSet.create(doc, decorations);
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
      toggleFocusMode:
        () =>
        ({ tr, dispatch }: any) => {
          if (dispatch) {
            const newEnabled = !this.storage.enabled;
            tr.setMeta('focusModeEnabled', newEnabled);
          }
          return true;
        },
      setFocusMode:
        (enabled: boolean) =>
        ({ tr, dispatch }: any) => {
          if (dispatch) {
            tr.setMeta('focusModeEnabled', enabled);
          }
          return true;
        },
    } as any;
  },
});
