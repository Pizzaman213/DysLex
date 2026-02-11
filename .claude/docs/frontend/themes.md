# Themes — Cream & Night

## Purpose

Two themes optimized for dyslexic users. Both avoid harsh pure-black-on-white contrast. See [CLAUDE.md > Accessibility](../../../CLAUDE.md) for the full design philosophy.

## Cream Theme (Default)

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | #FAF6EE | Main background |
| `--bg-editor` | #FFFDF8 | Editor canvas |
| `--text-primary` | #2D2A24 | Body text (warm dark) |
| `--accent` | #E07B4C | Primary accent |

## Night Theme

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | #1A1A22 | Main background |
| `--bg-editor` | #1E1E28 | Editor canvas |
| `--text-primary` | #E8E4DC | Body text (warm off-white) |
| `--accent` | #F0935E | Brighter orange |

## Key Files

| File | Role |
|------|------|
| `frontend/src/styles/tokens.css` | Design tokens |
| `frontend/src/styles/themes/cream.css` | Cream theme |
| `frontend/src/styles/themes/night.css` | Night theme |
| `frontend/src/styles/global.css` | Base styles |

## Status

- [x] Both themes implemented with CSS custom properties
- [x] Correction colors adjusted per theme
- [x] Theme persistence in settings
- [ ] System preference detection (`prefers-color-scheme`)
