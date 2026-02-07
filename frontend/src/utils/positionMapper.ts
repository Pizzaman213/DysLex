import type { Editor } from '@tiptap/react';

/**
 * Build a mapping from plain-text character index to ProseMirror position.
 *
 * ProseMirror positions count node boundaries (e.g. the start of a <p> tag
 * adds +1), so a plain-text offset of 5 may correspond to PM position 6 or
 * more depending on the document structure. This function walks the document
 * and builds a lookup array so we can translate plain-text offsets from the
 * correction API into PM positions for decorations.
 *
 * Returns an array where `map[plainIndex]` = PM position.
 * The array has length `plainTextLength + 1` so that `map[plainTextLength]`
 * gives the position just past the last character.
 */
export function buildPlainToPMMap(editor: Editor): number[] {
  const doc = editor.state.doc;
  const map: number[] = [];

  doc.descendants((node, pos) => {
    if (node.isText && node.text) {
      for (let i = 0; i < node.text.length; i++) {
        map.push(pos + i);
      }
    } else if (node.isBlock && map.length > 0) {
      // Block boundaries act as newlines in editor.getText()
      // TipTap's getText() inserts '\n' between blocks
      map.push(pos);
    }
    return true; // descend into children
  });

  // Add one past the end for exclusive end positions
  map.push(map.length > 0 ? map[map.length - 1] + 1 : 1);

  return map;
}

/**
 * Map a plain-text range [start, end) to ProseMirror positions.
 * Returns null if the range is out of bounds.
 */
export function mapRangeToPM(
  map: number[],
  start: number,
  end: number
): { start: number; end: number } | null {
  if (start < 0 || end > map.length - 1 || start >= end) {
    return null;
  }
  return { start: map[start], end: map[end] };
}
