# Module 12: Export & Sharing - Documentation

## Overview

This module adds document export and sharing capabilities to DysLex AI's TipTap editor. Users can export their work in multiple formats (DOCX, PDF, HTML, plain text) while preserving formatting. A Share Dialog provides link sharing with placeholders for future collaboration features.

## Features Implemented

### 1. Export Functionality

Export documents in four formats:

- **DOCX**: Microsoft Word format with formatting preserved
- **PDF**: Print-ready format with accessible fonts
- **HTML**: Complete standalone HTML document with embedded styles
- **Plain Text**: Basic text with optional metadata

#### Export Options

All exports support:
- Automatic title extraction (from H1 → first paragraph → "Untitled Document")
- Metadata inclusion (title, date, author)
- Proper filename generation with timestamp

#### Usage

```typescript
import { exportDOCX, exportPDF, exportHTML, exportPlainText } from './services/exportService';

// Export as DOCX
const result = await exportDOCX(editor.getHTML(), {
  title: 'My Document',
  author: 'John Doe',
  includeMetadata: true
});

if (result.success) {
  console.log('Export successful!');
} else {
  console.error('Export failed:', result.error);
}
```

### 2. Dialog Component

Reusable modal component with:
- Portal rendering to document.body
- Focus trap (Tab/Shift+Tab cycles within dialog)
- Escape key to close
- Backdrop click to close
- Accessible ARIA attributes
- Automatic focus management
- Body scroll prevention when open

#### Usage

```typescript
import { Dialog } from './components/Shared/Dialog';

<Dialog
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="My Dialog"
  size="md"
>
  <p>Dialog content goes here</p>
</Dialog>
```

### 3. ExportMenu Component

Dropdown menu integrated into EditorToolbar with:
- Keyboard navigation (Arrow keys, Enter, Escape)
- Four export format options
- Share dialog trigger
- Loading states during export
- Toast notifications for feedback

#### Keyboard Navigation

- **Arrow Down/Up**: Navigate menu items
- **Enter/Space**: Activate selected item
- **Escape**: Close menu

### 4. ShareDialog Component

Modal for sharing documents with:
- **Copy Link**: Generates placeholder shareable URL and copies to clipboard
- **Email Share**: Stub button with "coming soon" message
- **Info Section**: Explains upcoming collaboration features

#### Current Behavior

- Link format: `https://dyslex.ai/doc/{random-id}`
- Links are placeholders (no backend storage yet)
- Clipboard API with fallback for older browsers

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Editor/
│   │   │   ├── ExportMenu.tsx          # Export dropdown menu
│   │   │   ├── ShareDialog.tsx         # Share modal
│   │   │   └── EditorToolbar.tsx       # Updated with ExportMenu
│   │   └── Shared/
│   │       ├── Dialog.tsx              # Reusable modal component
│   │       └── index.ts                # Updated exports
│   ├── services/
│   │   └── exportService.ts            # Export logic for all formats
│   └── styles/
│       └── global.css                  # Dialog, menu, and share styles
└── package.json                        # Added export dependencies
```

## Dependencies Added

```json
{
  "html-to-docx": "^1.8.0",      // DOCX export from HTML
  "html2pdf.js": "^0.10.1",      // PDF export with multi-page support
  "file-saver": "^2.0.5",        // Cross-browser file downloads
  "@types/file-saver": "^2.0.7"  // TypeScript types
}
```

**Bundle size impact**: ~555KB total (minified)

## Styling

All styles added to `global.css`:

### Dialog Styles
- `.dialog-backdrop`: Overlay with 50% opacity
- `.dialog`: Modal container with three sizes (sm/md/lg)
- `.dialog__header`: Title and close button
- `.dialog__body`: Main content area
- `.dialog__footer`: Action buttons area

### Export Menu Styles
- `.export-menu__dropdown`: Positioned dropdown
- `.export-menu__item`: Menu items with hover states
- `.export-menu__separator`: Divider line
- Keyboard focus states

### Share Dialog Styles
- `.share-dialog__section`: Content sections
- `.share-dialog__link-display`: Monospace URL display
- `.share-dialog__button`: Primary and secondary button styles
- `.share-dialog__info`: Information box with accent border

## Accessibility Features

### Dialog Component
- `role="dialog"` and `aria-modal="true"`
- `aria-labelledby` pointing to title
- Focus trap implementation
- Escape key closes dialog
- Focus returns to trigger element on close
- Body scroll prevented when open

### ExportMenu Component
- `aria-expanded` and `aria-haspopup` on trigger button
- `role="menu"` and `role="menuitem"` for dropdown
- `tabindex` management for keyboard navigation
- Visual focus indicators

### ShareDialog Component
- Clear button labels
- Toast notifications for all actions
- High contrast buttons
- Descriptive information text

## Testing

### Manual Testing

#### Export Functionality
1. Create document with headings, lists, formatting
2. Export as each format (DOCX, PDF, HTML, TXT)
3. Verify formatting preserved
4. Test edge cases (empty document, long document, special characters)

#### Dialog Behavior
1. Open dialog → verify backdrop appears
2. Press Escape → dialog closes
3. Click backdrop → dialog closes
4. Tab through elements → focus stays trapped
5. Close dialog → focus returns to trigger

#### Share Dialog
1. Click "Copy Link" → clipboard contains URL
2. Click "Email Share" → toast shows "coming soon"
3. Test on different browsers (Chrome, Firefox, Safari)

#### Keyboard Navigation
1. Open export menu with click
2. Use Arrow keys to navigate
3. Press Enter to activate item
4. Press Escape to close menu

### Theme Testing
- Test in Cream theme
- Test in Night theme
- Verify backdrop opacity
- Check button contrast ratios

### Browser Testing
- Chrome/Edge (primary)
- Firefox
- Safari
- Mobile Safari (responsive dialog)

## Future Enhancements

### Backend Integration (Phase 2)
- Real shareable links with backend storage
- Document versioning
- Expiration dates for shared links
- Password protection

### Collaboration Features (Phase 3)
- Real-time collaborative editing (Yjs/ShareDB)
- Presence indicators
- Comments and suggestions
- Version history with diffs

### Export Improvements
- Custom export templates (letterhead, academic formats)
- Batch export (multiple documents)
- Export settings dialog (page size, margins, fonts)
- Export with corrections highlighted
- Export to cloud storage (Google Drive, Dropbox)

### Share Enhancements
- Email sharing integration
- Social media sharing
- Embedded document viewer
- Permission controls (view/edit)

## Known Limitations

### Current Phase
1. **Shareable links are placeholders**: No backend storage yet
2. **PDF fonts**: Custom dyslexia fonts may fall back to system fonts in PDF export
3. **DOCX styling**: Complex styles may not convert perfectly
4. **No collaboration**: Sharing is one-way (export only)

### Technical Notes
- PDF generation happens client-side (may be slow for large documents)
- DOCX conversion best suited for standard formatting
- HTML export includes all styles inline (larger file size)
- Plain text export loses all formatting (by design)

## Troubleshooting

### Export Fails
- Check browser console for errors
- Verify document isn't empty
- Try exporting smaller section first
- Clear browser cache and retry

### PDF Issues
- Large images may cause memory issues
- Very long documents may timeout
- Custom fonts may not embed

### Dialog Not Closing
- Check if multiple dialogs are open
- Verify `onClose` handler is connected
- Test Escape key and backdrop click separately

### Clipboard Copy Fails
- Browser may block clipboard access
- Check permissions (clipboard-write)
- Fallback execCommand should work on older browsers

## API Reference

### exportService.ts

#### `exportDOCX(html: string, options?: ExportOptions): Promise<ExportResult>`
Exports document as Microsoft Word format.

#### `exportPDF(html: string, options?: ExportOptions): Promise<ExportResult>`
Exports document as PDF with multi-page support.

#### `exportHTML(html: string, options?: ExportOptions): Promise<ExportResult>`
Exports complete standalone HTML document.

#### `exportPlainText(text: string, options?: ExportOptions): Promise<ExportResult>`
Exports plain text with optional metadata.

#### `generateFilename(title: string, extension: string): string`
Generates sanitized filename with timestamp.

#### `extractTitle(html: string): string`
Extracts document title from HTML content.

#### `addDocumentMetadata(html: string, options: ExportOptions): string`
Adds metadata header to HTML content.

### Dialog.tsx

#### Props
```typescript
interface DialogProps {
  isOpen: boolean;        // Control visibility
  onClose: () => void;    // Close handler
  title: string;          // Dialog title
  children: ReactNode;    // Dialog content
  size?: 'sm' | 'md' | 'lg';  // Size (400px | 600px | 800px)
  className?: string;     // Additional CSS classes
}
```

### ExportMenu.tsx

#### Props
```typescript
interface ExportMenuProps {
  editor: ReturnType<typeof useEditor>;  // TipTap editor instance
}
```

### ShareDialog.tsx

#### Props
```typescript
interface ShareDialogProps {
  isOpen: boolean;     // Control visibility
  onClose: () => void; // Close handler
}
```

## Contributing

When modifying export functionality:
1. Update tests for new formats
2. Verify accessibility (keyboard nav, screen readers)
3. Test in both themes
4. Check bundle size impact
5. Update this documentation

## Related Modules

- **Module 8**: Shared UI components (basis for Dialog)
- **Module 11**: Toast notifications (used for export feedback)
- **TipTap Editor**: Source of content for export

## Resources

- [html-to-docx documentation](https://github.com/privateOmega/html-to-docx)
- [html2pdf.js documentation](https://ekoopmans.github.io/html2pdf.js/)
- [FileSaver.js documentation](https://github.com/eligrey/FileSaver.js)
- [WAI-ARIA Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
