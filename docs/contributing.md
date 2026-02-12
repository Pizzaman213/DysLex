# Contributing to DysLex AI

Thank you for your interest in contributing!

---

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a branch for your feature/fix
4. Make your changes
5. Submit a pull request

See [quickstart.md](quickstart.md) for development environment setup.

---

## Code Style

### Frontend (TypeScript/React)
- Functional components with hooks only
- ES modules (import/export), never CommonJS
- `camelCase` for variables/functions, `PascalCase` for components/classes, `UPPER_SNAKE_CASE` for constants
- Run `npm run lint` and `npm run type-check` before committing

### Backend (Python/FastAPI)
- Type hints required on all functions
- `snake_case` for variables/functions, `PascalCase` for classes
- Repository pattern for database access, async endpoints for I/O
- Run `ruff check app/` and `mypy app/ --ignore-missing-imports` before committing

---

## Accessibility

This is an accessibility-first project. All contributions must:
- Support keyboard navigation
- Include ARIA labels where appropriate
- Maintain WCAG AA color contrast (4.5:1 minimum)
- Work with screen readers
- Support dyslexia-friendly fonts (OpenDyslexic, Atkinson Hyperlegible)
- Use design tokens from `styles/tokens.css`
- Never interrupt creative flow with popups

---

## Testing

```bash
# Frontend
cd frontend
npm test
npm run type-check

# Backend
cd backend
pytest tests/
mypy app/ --ignore-missing-imports
ruff check app/
```

---

## Pull Request Process

1. Add tests for new functionality
2. Ensure all tests pass
3. Update documentation if needed
4. Request review from maintainers

---

## API Reference

Base URL: `http://localhost:8000/api`

### Corrections

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/corrections` | Get text corrections using the two-tier LLM system |
| POST | `/corrections/quick` | Quick correction using local model only |

**POST /corrections:**
```json
// Request
{ "text": "Teh quick brown fox jumps over the lazzy dog.", "context": "Academic writing" }

// Response
{
  "corrections": [{
    "original": "Teh", "suggested": "The", "type": "transposition",
    "start": 0, "end": 3, "confidence": 0.98, "explanation": "Letters were swapped"
  }]
}
```

### Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/profiles/me` | Get current user's error profile |
| PATCH | `/profiles/me` | Update current user's error profile |
| GET | `/profiles/me/patterns` | Get user's learned error patterns |
| GET | `/profiles/me/confusion-pairs` | Get user's common confusion pairs |

### Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/progress` | Get user's progress statistics |
| GET | `/progress/dashboard?weeks=12` | Get complete dashboard data |
| GET | `/progress/history` | Get historical progress data |
| GET | `/progress/achievements` | Get user's achievements |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/users` | Create a new user |
| GET | `/users/me` | Get current user's profile |
| PATCH | `/users/me` | Update current user's profile |
| DELETE | `/users/me` | Delete current user's account |

### Voice

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/tts` | Convert text to speech |
| POST | `/voice/stt` | Convert speech to text (multipart upload) |
| GET | `/voice/voices` | List available TTS voices |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (`{ "status": "healthy" }`) |

---

## Code of Conduct

Be respectful and inclusive. This project serves users with dyslexia and other learning differences. The user is intelligent — they need better tools, not simpler ideas.
