# Themes — Cream & Night

## Purpose

DysLex AI provides two carefully designed themes optimized for dyslexic users. Both avoid the harsh contrast of pure black on pure white, which can cause visual stress and reading fatigue.

## Cream Theme (Default)

The default theme uses warm, paper-like colors that reduce eye strain during extended writing sessions.

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | #FAF6EE | Main background, app shell |
| `--bg-secondary` | #F0EBE0 | Hover states, toolbar backgrounds |
| `--bg-editor` | #FFFDF8 | Editor page / writing canvas |
| `--bg-sidebar` | #F5F0E6 | Left sidebar, right panel |
| `--bg-card` | #FFFFFF | Cards, correction cards |
| `--text-primary` | #2D2A24 | Body text, headings (warm dark) |
| `--text-secondary` | #6B6560 | Descriptions, secondary labels |
| `--text-muted` | #9E9890 | Timestamps, placeholders |
| `--accent` | #E07B4C | Primary accent (buttons, active states) |
| `--accent-hover` | #C96A3E | Accent hover/pressed |
| `--success` | #5BA07A | Grammar corrections, progress |
| `--warning` | #D4A843 | Homophone warnings |
| `--blue` | #5B8FC7 | Clarity/structure badges |
| `--purple` | #9B7FC7 | Style badges |
| `--border` | #D4C9A8 | Borders, dividers |

### Correction Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-correction-spelling` | #f5d4d4 | Spelling errors |
| `--color-correction-grammar` | #d4e4f5 | Grammar issues |
| `--color-correction-confusion` | #f5e4d4 | Word confusion |
| `--color-correction-phonetic` | #e4f5d4 | Phonetic substitutions |

## Night Theme

For users who prefer dark mode or write in low-light environments. Uses dark blue-gray (not pure black) to reduce harshness.

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | #1A1A22 | Main background (dark blue-gray) |
| `--bg-secondary` | #22222C | Hover states, elevated surfaces |
| `--bg-editor` | #1E1E28 | Editor writing canvas |
| `--bg-sidebar` | #16161E | Sidebar, panel backgrounds |
| `--bg-card` | #24242E | Cards, toggles |
| `--text-primary` | #E8E4DC | Body text (warm off-white) |
| `--text-secondary` | #B8B8B8 | Descriptions |
| `--text-muted` | #888888 | Timestamps, hints |
| `--accent` | #F0935E | Brighter orange for contrast |
| `--accent-hover` | #E08550 | Accent hover |
| `--success` | #6BB88A | Brighter green |
| `--warning` | #E0B84D | Brighter yellow |
| `--blue` | #6B9FD7 | Adjusted for dark bg |
| `--purple` | #AB8FD7 | Adjusted for dark bg |
| `--border` | #3A3A5C | Borders, dividers |

### Correction Colors (Night)
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-correction-spelling` | #4a3535 | Spelling errors |
| `--color-correction-grammar` | #35454a | Grammar issues |
| `--color-correction-confusion` | #4a4535 | Word confusion |
| `--color-correction-phonetic` | #3a4a35 | Phonetic substitutions |

## Implementation

### CSS Custom Properties

```css
/* frontend/src/styles/tokens.css */
:root {
  /* Default to Cream theme */
  --color-bg-primary: #fdf6e3;
  --color-text-primary: #3d3d3d;
  /* ... */
}

/* frontend/src/styles/themes/cream.css */
.theme-cream {
  --color-bg-primary: #fdf6e3;
  /* ... */
}

/* frontend/src/styles/themes/night.css */
.theme-night {
  --color-bg-primary: #1a1a2e;
  /* ... */
}
```

### Theme Switching

```typescript
// frontend/src/stores/settingsStore.ts
export const useSettingsStore = create(
  persist(
    (set) => ({
      theme: 'cream',  // or 'night'
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'dyslex-settings' }
  )
);

// frontend/src/components/Shared/ThemeSwitcher.tsx
export function ThemeSwitcher() {
  const { theme, setTheme } = useSettingsStore();

  return (
    <button
      onClick={() => setTheme(theme === 'cream' ? 'night' : 'cream')}
      aria-label={`Switch to ${theme === 'cream' ? 'night' : 'cream'} theme`}
    >
      {theme === 'cream' ? '🌙' : '☀️'}
    </button>
  );
}
```

### Applying Theme

```tsx
// frontend/src/App.tsx
export function App() {
  const { theme } = useSettingsStore();

  return (
    <div className={`app theme-${theme}`}>
      {/* App content */}
    </div>
  );
}
```

## Key Files

- `frontend/src/styles/tokens.css` — Design tokens
- `frontend/src/styles/themes/cream.css` — Cream theme
- `frontend/src/styles/themes/night.css` — Night theme
- `frontend/src/stores/settingsStore.ts` — Theme state
- `frontend/src/components/Shared/ThemeSwitcher.tsx` — Toggle UI

## Accessibility Notes

- Both themes meet WCAG AA contrast ratios
- Correction colors adjusted per theme for visibility
- No pure black or pure white in either theme
- Transition between themes is smooth (250ms)

## User Preferences

Theme selection is:
- Persisted to localStorage
- Synced across sessions
- Respects system preference (optional future feature)

## Status

- [x] Cream theme designed
- [x] Night theme designed
- [x] CSS variables implemented
- [x] Theme switcher component
- [x] Settings persistence
- [ ] System preference detection
- [ ] Additional theme options (blue tint, etc.)
