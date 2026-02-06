# Design Tokens

## Color System

### Cream Theme (Default)
```css
--color-bg-primary: #fdf6e3;
--color-bg-secondary: #f5eed6;
--color-bg-tertiary: #eee8c5;
--color-text-primary: #3d3d3d;
--color-text-secondary: #5a5a5a;
--color-accent: #4a90a4;
```

### Night Theme
```css
--color-bg-primary: #1a1a2e;
--color-bg-secondary: #252542;
--color-bg-tertiary: #2d2d4a;
--color-text-primary: #e8e8e8;
--color-text-secondary: #b8b8b8;
--color-accent: #6ab0c4;
```

### Correction Colors
```css
--color-correction-spelling: soft red
--color-correction-grammar: soft blue
--color-correction-confusion: soft orange
--color-correction-phonetic: soft green
```

## Typography

### Fonts
- **OpenDyslexic** - Designed specifically for dyslexic readers
- **Atkinson Hyperlegible** - High legibility font
- **Lexie Readable** - Clear, readable font

### Sizes
```css
--font-size-sm: 0.875rem;
--font-size-base: 1rem;
--font-size-lg: 1.125rem;
--font-size-xl: 1.25rem;
--font-size-2xl: 1.5rem;
```

### Line Height
```css
--line-height-tight: 1.25;
--line-height-normal: 1.5;
--line-height-relaxed: 1.75;
```

## Spacing

```css
--space-xs: 0.25rem;
--space-sm: 0.5rem;
--space-md: 1rem;
--space-lg: 1.5rem;
--space-xl: 2rem;
--space-2xl: 3rem;
```

## Accessibility

### Contrast Ratios
- Text on background: minimum 4.5:1 (WCAG AA)
- Large text: minimum 3:1

### Focus States
```css
--focus-ring: 0 0 0 3px rgba(74, 144, 164, 0.4);
```

### Touch Targets
- Minimum size: 44x44px
