# Accessibility — Dyslexia-Friendly Design

## Purpose

Every design decision prioritizes dyslexic users. The interface must look like a normal word processor — nobody should be able to tell it's assistive software. See [CLAUDE.md > Accessibility](../../../CLAUDE.md) for full requirements.

## Typography

- **Fonts**: OpenDyslexic, Atkinson Hyperlegible (heavy bottom-weighted, maximum differentiation)
- **Size**: 16px minimum, 18px default editor content
- **Line spacing**: 1.5 minimum, 1.75 default
- **Letter spacing**: 0.05-0.12em (prevents crowding)

## Color & Contrast

- No pure black (#000) on pure white (#FFF)
- WCAG AA contrast ratios (4.5:1 for normal text)
- Color never the only indicator — always paired with icons/text
- Correction underlines: subtle pastels, not aggressive red

## Key Rules

- All interactive elements: 44x44px minimum touch targets
- Focus visible on every element (box-shadow outline)
- `prefers-reduced-motion` respected
- No flashing, strobing, or rapid animations
- Screen reader support with `aria-live`, `aria-label`, semantic HTML
- Progress always framed positively (never "errors made")

## Key Files

| File | Role |
|------|------|
| `frontend/src/styles/tokens.css` | Design tokens |
| `frontend/src/styles/global.css` | Base accessible styles |
| `.claude/rules/frontend/accessibility.md` | Claude rules for a11y |

## Status

- [x] Design tokens and themes
- [x] Dyslexia-friendly fonts
- [x] WCAG AA contrast
- [ ] Full keyboard navigation audit
- [ ] Screen reader testing
- [ ] Reduced motion support
