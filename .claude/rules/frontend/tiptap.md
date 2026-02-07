---
paths:
  - "frontend/src/components/Editor/**"
---

# TipTap Editor Guidelines

## Extensions

- Use TipTap extensions for all editor features
- Keep custom extensions minimal
- Document extension configurations

## Corrections

- Correction overlays use the decoration plugin
- Never block the main editing flow
- Corrections appear inline, no popups

## Passive Learning

- Snapshots taken every 5-10 seconds
- Store snapshots in memory only
- Compute diff on pause/blur

## Performance

- Debounce input handlers
- Lazy load heavy extensions
- Use virtualization for long documents

## Example Extension

```typescript
import { Extension } from '@tiptap/core';

export const CorrectionHighlight = Extension.create({
  name: 'correctionHighlight',

  addProseMirrorPlugins() {
    return [
      // Decoration plugin for highlighting corrections
    ];
  },
});
```
