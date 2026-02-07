# Accessibility — Dyslexia-Friendly Design

## Purpose

DysLex AI is an accessibility-first application. Every design decision prioritizes dyslexic users. The interface must look like a normal word processor — nobody should be able to tell it's assistive software by looking at someone's screen.

**Core principle**: Invisible assistance. The best accessibility features are the ones users don't notice because they just work.

## Typography Requirements

### Fonts
DysLex AI includes three dyslexia-friendly font options:

| Font | Description | Best For |
|------|-------------|----------|
| OpenDyslexic | Heavy bottom-weighted letters prevent rotation | Users with letter reversal issues |
| Atkinson Hyperlegible | Maximum character differentiation | General readability |
| Lexie Readable | Clean, clear letterforms | Users who find OpenDyslexic too stylized |

**Implementation**:
```css
--font-family-display: 'OpenDyslexic', 'Atkinson Hyperlegible', sans-serif;
--font-family-body: 'OpenDyslexic', 'Atkinson Hyperlegible', sans-serif;
```

### Font Size
- Minimum: 16px base (never smaller)
- Default: 18px for editor content
- User adjustable: 14px to 24px range
- Always use `rem`/`em`, never `px` for text

### Line Spacing
- Minimum: 1.5 line-height
- Default: 1.75 for editor content
- User adjustable: 1.2 to 2.0 range

### Letter Spacing
- Default: Slightly increased (0.05-0.12em)
- Helps prevent letter crowding

## Color & Contrast

### Avoid Pure Black on White
Pure black (#000) on pure white (#FFF) creates harsh contrast that causes visual stress. Instead:

**Cream Theme (Default)**:
```css
--bg-primary: #FAF6EE;      /* Warm off-white */
--text-primary: #2D2A24;    /* Dark gray, not black */
```

**Night Theme**:
```css
--bg-primary: #1A1A22;      /* Dark blue-gray, not pure black */
--text-primary: #E8E4DC;    /* Warm off-white, not pure white */
```

### Contrast Requirements
- Body text: WCAG AA minimum (4.5:1)
- Large text: 3:1 minimum
- Interactive elements: Visible in all themes

### Color Never Alone
Color must never be the only indicator. Always pair with:
- Icons
- Text labels
- Patterns or shapes

Example: Correction underlines use color + underline style.

## Correction Indicators

### Underline Colors (Subtle, Not Aggressive)
```css
/* Cream Theme */
--color-correction-spelling: #f5d4d4;   /* Soft coral */
--color-correction-grammar: #d4e4f5;     /* Soft blue */
--color-correction-confusion: #f5e4d4;   /* Soft orange */
--color-correction-phonetic: #e4f5d4;    /* Soft green */
```

### Never Use
- Aggressive red underlines
- Flashing or blinking
- Large intrusive popups
- Sounds for errors

## Focus States

Every interactive element must have a visible focus state:

```css
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(74, 144, 164, 0.4);
}
```

Focus order must be logical and match visual order.

## Touch Targets

- Minimum size: 44x44px for all interactive elements
- Adequate spacing between targets
- No precision required for core functions

## Keyboard Navigation

All features must be keyboard accessible:

| Action | Keyboard |
|--------|----------|
| Navigate UI | Tab / Shift+Tab |
| Activate | Enter / Space |
| Close/Cancel | Escape |
| Navigate options | Arrow keys |
| Skip to content | Skip link |

## Screen Reader Support

- All images have `alt` text
- All interactive elements have `aria-label`
- Dynamic content uses `aria-live` regions
- Form inputs have associated labels
- Semantic HTML throughout

## Motion & Animation

- Respect `prefers-reduced-motion`
- No rapid animations (nothing faster than 250ms)
- No flashing or strobing
- Smooth, subtle transitions only

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Reading Support

### Read Aloud (MagpieTTS)
- Natural human-sounding voice
- Adjustable speed
- Word highlighting as it reads
- Available on all text

### Focus Mode
- Dims everything except current paragraph
- Reduces visual distraction
- User-activated, never forced

## Progress Framing

All metrics must be positive:
- ✅ "Words written today: 500"
- ✅ "Words mastered: 12"
- ✅ "Writing streak: 5 days"
- ❌ "Errors made: 23"
- ❌ "Mistakes fixed: 15"

## Implementation Checklist

For every new feature, verify:

- [ ] Works with keyboard only
- [ ] Screen reader announces correctly
- [ ] Focus is visible and logical
- [ ] Touch targets are 44x44px+
- [ ] Color is not the only indicator
- [ ] Contrast meets WCAG AA
- [ ] Respects reduced motion
- [ ] Works in both themes
- [ ] No flashing or rapid animation
- [ ] Progress framed positively

## Key Files

- `frontend/src/styles/tokens.css` — Design tokens
- `frontend/src/styles/themes/cream.css` — Light theme
- `frontend/src/styles/themes/night.css` — Dark theme
- `frontend/src/styles/global.css` — Base styles
- `.claude/rules/frontend/accessibility.md` — Claude rules

## Status

- [x] Design tokens created
- [x] Themes implemented
- [x] Font options available
- [ ] Full keyboard navigation
- [ ] Screen reader testing
- [ ] Reduced motion support
- [ ] Focus mode implementation
