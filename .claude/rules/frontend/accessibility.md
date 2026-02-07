---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
---

# Accessibility Requirements

## Focus States

- All interactive elements need visible focus states
- Focus ring: `box-shadow: var(--focus-ring)`
- Never hide focus outlines

## Semantic HTML

- Use `<button>` for actions, not `<div>`
- Use `<nav>`, `<main>`, `<article>`, `<section>`
- Headings in logical order (h1, h2, h3...)

## ARIA

- Images require `alt` text
- Form inputs need associated `<label>`
- Use `aria-label` for icon-only buttons
- Use `role` attributes when semantic HTML isn't enough

## Color

- Color must not be the only indicator
- Minimum contrast ratio 4.5:1 (WCAG AA)
- Test with color blindness simulators

## Keyboard

- All interactive elements must be keyboard accessible
- Logical tab order
- Escape key closes modals

## Touch

- Minimum touch target: 44x44px
- Adequate spacing between targets

## Units

- Use `rem`/`em` for font sizes, not `px`
- Respect user's font size preferences

## Motion

- Support `prefers-reduced-motion`
- No rapid animations or flashing
