---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.ts"
---

# React Patterns

## Component Structure

- Functional components with hooks only
- Use ES modules (import/export), never CommonJS
- Destructure imports: `import { Component } from './module'`

## State Management

- Use Zustand for global state
- Keep component state minimal
- Derive data when possible

## Hooks

- Custom hooks for reusable logic
- Use `use` prefix for custom hooks
- Keep hooks at top of component

## Props

- Define prop types with TypeScript interfaces
- Use destructuring in function parameters
- Provide default values when appropriate

## Example Component

```tsx
interface ButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export function Button({ label, onClick, disabled = false }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="btn"
      aria-label={label}
    >
      {label}
    </button>
  );
}
```
