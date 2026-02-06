# Contributing to DysLex AI

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a branch for your feature/fix
4. Make your changes
5. Submit a pull request

## Development Setup

See [deployment.md](deployment.md) for development environment setup.

## Code Style

### Frontend (TypeScript/React)
- Functional components with hooks
- ES modules only
- Run `npm run lint` before committing
- Run `npm run type-check` for type errors

### Backend (Python/FastAPI)
- Type hints required on all functions
- Run `ruff check app/` for linting
- Run `mypy app/` for type checking
- Follow PEP 8

## Accessibility

This is an accessibility-first project. All contributions must:
- Support keyboard navigation
- Include ARIA labels where appropriate
- Maintain WCAG AA color contrast
- Work with screen readers
- Support dyslexia-friendly fonts

## Testing

### Frontend
```bash
npm test
```

### Backend
```bash
pytest tests/
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Request review from maintainers

## Code of Conduct

Be respectful and inclusive. This project serves users with dyslexia and other learning differences.
