import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { useFormatStore } from '../../../stores/formatStore';

export const ParagraphIndentExtension = Extension.create({
  name: 'paragraphIndent',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('paragraphIndent'),
        props: {
          decorations(state) {
            const { activeFormat } = useFormatStore.getState();
            if (activeFormat === 'none') return DecorationSet.empty;

            const decorations: Decoration[] = [];

            state.doc.descendants((node, pos) => {
              if (node.type.name === 'paragraph' && node.content.size > 0) {
                decorations.push(
                  Decoration.node(pos, pos + node.nodeSize, {
                    style: 'text-indent: 0.5in',
                  })
                );
              }
            });

            return DecorationSet.create(state.doc, decorations);
          },
        },
      }),
    ];
  },
});
