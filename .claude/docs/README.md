# Claude Documentation Directory

This folder contains feature documentation that Claude must read before implementing or modifying any features. **Always check the relevant doc file before making changes.**

## How To Use This Folder

1. **Before implementing a feature**: Read the corresponding doc file to understand requirements
2. **After implementing a feature**: Update the doc file with implementation details
3. **When adding new features**: Create a new doc file following the template

## Documentation Index

### Core Systems
- `three-model-architecture.md` — The three AI models and how they work together
- `adaptive-learning-loop.md` — Passive learning system (the secret sauce)
- `error-profile-system.md` — User error pattern tracking

### Writing Modes
- `capture-mode.md` — Voice-to-thought capture
- `mindmap-mode.md` — Visual idea organization
- `draft-mode.md` — Scaffolded writing with corrections
- `polish-mode.md` — Review and refinement

### Editor Features
- `tiptap-editor.md` — Core editor implementation
- `correction-overlay.md` — Inline correction display
- `snapshot-engine.md` — Text snapshot and diff system

### Voice Features
- `voice-input.md` — Speech-to-text via faster-whisper
- `text-to-speech.md` — Read-aloud via MagpieTTS

### User Experience
- `accessibility.md` — Dyslexia-friendly design requirements
- `themes.md` — Cream and Night theme system
- `progress-dashboard.md` — User improvement tracking

### Backend Services
- `llm-orchestrator.md` — Two-tier LLM processing
- `nim-integration.md` — NVIDIA NIM API usage
- `database-schema.md` — PostgreSQL tables and relationships

## Documentation Template

When creating new feature docs, use this structure:

```markdown
# Feature Name

## Purpose
Why this feature exists and what problem it solves for dyslexic users.

## User Experience
How the user interacts with this feature. Remember: invisible is better.

## Technical Implementation
### Frontend
- Components involved
- State management
- Key files

### Backend
- API endpoints
- Services
- Database tables

## Accessibility Requirements
- WCAG compliance
- Keyboard navigation
- Screen reader support

## Integration Points
How this feature connects to other parts of the system.

## Status
- [ ] Designed
- [ ] Frontend implemented
- [ ] Backend implemented
- [ ] Tested
- [ ] Documented
```

## Rules For Claude

1. **Always read before implementing** — Check the doc file first
2. **Update docs after changes** — Keep documentation in sync with code
3. **Follow the philosophy** — Every feature must serve dyslexic users
4. **No accept/reject buttons** — Passive learning is core
5. **Invisible assistance** — The best features are ones users don't notice
