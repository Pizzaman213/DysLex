/**
 * Tracked Changes Extension
 *
 * TipTap extension for displaying tracked changes (insertions/deletions)
 * in Polish Mode with visible decorations
 */

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { TrackedChange } from '../../../stores/polishStore';

export interface TrackedChangesOptions {
  onSuggestionClick?: (suggestionId: string, position: { start: number; end: number }) => void;
}

export const TrackedChangesExtension = Extension.create<TrackedChangesOptions>({
  name: 'trackedChanges',

  addOptions() {
    return {
      onSuggestionClick: undefined,
    };
  },

  addProseMirrorPlugins() {
    const extensionThis = this;

    return [
      new Plugin({
        key: new PluginKey('trackedChanges'),
        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, set) {
            // Get suggestions from transaction metadata
            const suggestions = tr.getMeta('trackedChanges');
            if (suggestions !== undefined) {
              return createDecorations(suggestions, extensionThis.options.onSuggestionClick);
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
      setTrackedChanges:
        (suggestions: TrackedChange[]) =>
        ({ tr, dispatch }: any) => {
          if (dispatch) {
            tr.setMeta('trackedChanges', suggestions);
          }
          return true;
        },
    } as any;
  },
});

/**
 * Create decorations for tracked changes
 */
function createDecorations(
  suggestions: TrackedChange[],
  onSuggestionClick?: (suggestionId: string, position: { start: number; end: number }) => void
): DecorationSet {
  const decorations: Decoration[] = [];

  suggestions.forEach((suggestion) => {
    // Skip applied or dismissed suggestions
    if (suggestion.isApplied || suggestion.isDismissed) {
      return;
    }

    // Create decoration based on change type
    if (suggestion.type === 'insert') {
      // Green underline for insertions
      const decoration = Decoration.inline(
        suggestion.start,
        suggestion.end,
        {
          class: 'tracked-insertion tracked-change',
          'data-suggestion-id': suggestion.id,
          'aria-description': `Suggested insertion: ${suggestion.text}`,
        },
        {
          suggestion,
          onSuggestionClick,
        }
      );
      decorations.push(decoration);
    } else if (suggestion.type === 'delete') {
      // Red strikethrough for deletions
      const decoration = Decoration.inline(
        suggestion.start,
        suggestion.end,
        {
          class: 'tracked-deletion tracked-change',
          'data-suggestion-id': suggestion.id,
          'aria-description': `Suggested deletion: ${suggestion.original}`,
        },
        {
          suggestion,
          onSuggestionClick,
        }
      );
      decorations.push(decoration);
    } else if (suggestion.type === 'replace') {
      // Replacement: deletion followed by insertion
      // Show deletion at original position
      const deletionDecoration = Decoration.inline(
        suggestion.start,
        suggestion.end,
        {
          class: 'tracked-deletion tracked-change',
          'data-suggestion-id': suggestion.id,
          'aria-description': `Suggested replacement: ${suggestion.original} → ${suggestion.text}`,
        },
        {
          suggestion,
          onSuggestionClick,
        }
      );
      decorations.push(deletionDecoration);

      // Note: Insertion decoration would be at same position
      // For simplicity, we show only deletion with aria-description indicating replacement
    }
  });

  return DecorationSet.create(
    {
      childCount: 0,
      content: { size: 0 },
      nodeSize: 0,
    } as any,
    decorations
  );
}

/**
 * Global click handler for tracked changes
 */
if (typeof document !== 'undefined') {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const changeEl = target.closest('.tracked-change');

    if (changeEl) {
      const suggestionId = changeEl.getAttribute('data-suggestion-id');
      if (suggestionId) {
        const rect = changeEl.getBoundingClientRect();
        // Dispatch custom event
        const event = new CustomEvent('tracked-change-click', {
          detail: { suggestionId, rect },
        });
        document.dispatchEvent(event);
      }
    }
  });
}
