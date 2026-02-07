# DysLex AI — Project Memory

> "The goal isn't to fix how someone writes — it's to free the ideas already inside them."

## Mission & Philosophy

DysLex AI is an open source, adaptive AI writing tool built specifically for dyslexic thinkers. Dyslexia isn't a deficit — it's a different cognitive architecture. Dyslexic thinkers often excel at big-picture reasoning, pattern recognition, spatial thinking, and creative problem-solving. The challenge isn't a lack of ideas; it's that traditional writing mechanics create friction between brilliant thinking and the page.

### Core Design Principles

1. **Voice-first, text-second**: Dyslexic thinkers often express ideas better verbally. Voice input is a first-class citizen, not an afterthought.

2. **Structure emerges, not imposed**: Don't start with an outline template. Let ideas flow freely, then help organize them. The tool finds the structure hidden in scattered thoughts.

3. **Corrections are invisible**: Never interrupt the creative flow. Fix spelling and grammar silently in the background. The writer should never feel "corrected" while generating ideas.

4. **Show progress, not deficits**: Every metric frames improvement positively. "You've written 500 words today!" — never "You made 23 errors."

5. **Respect the person**: The user is intelligent. They don't need simpler ideas — they need better tools for expressing complex ones.

### What Makes This Different

Existing tools either use old spell-check algorithms that fail on severe dyslexic misspellings, or they use AI but don't personalize to the individual. DysLex AI combines three things nobody has put together properly:

- A **per-user adaptive error profile** that learns individual patterns
- A **fast local correction model** for instant feedback
- A **powerful LLM** for deep contextual understanding

The feedback loop between these components means the tool genuinely gets smarter for each person who uses it.

---

## Quick Start

```bash
# Unified Launcher (Recommended - ONE COMMAND!)
python3 run.py --auto-setup

# Or individual services
# Frontend (port 3000)
cd frontend && npm install && npm run dev

# Backend (port 8000)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Full stack with Docker
docker compose -f docker/docker-compose.yml up

# Development with Claude Code + Chrome
claude --chrome  # then navigate to localhost:3000
```

---

## Claude Code Integration (MCP Tools)

This project includes an **MCP (Model Context Protocol) server** that provides tools for controlling DysLex AI services directly from Claude Code. When working on this project, you have access to these tools:

### Available MCP Tools

#### dyslex_start
Start DysLex AI services with various options.

**Parameters:**
- `mode` (string): 'dev' (default), 'docker', 'backend', or 'frontend'
- `auto_setup` (boolean): Auto-start PostgreSQL/Redis, create venv, install deps, kill ports (default: false)
- `backend_port` (integer): Backend port (default: 8000)
- `frontend_port` (integer): Frontend port (default: 3000)

**Usage:**
```python
# Start with auto-setup (handles everything automatically)
dyslex_start(auto_setup=True)

# Start in Docker mode
dyslex_start(mode="docker")

# Start with custom ports
dyslex_start(backend_port=8080, frontend_port=3001)
```

#### dyslex_stop
Stop all DysLex AI services gracefully.

**Usage:**
```python
dyslex_stop()
```

#### dyslex_status
Check service status and health. Returns process status, port status for all services (backend, frontend, PostgreSQL, Redis), and access URLs.

**Usage:**
```python
dyslex_status()
```

#### dyslex_logs
View recent logs from services (note: simplified in current implementation).

**Parameters:**
- `lines` (integer): Number of lines to show (default: 50)
- `service` (string): Filter by 'all', 'backend', 'frontend', 'system' (default: 'all')

**Usage:**
```python
dyslex_logs(lines=100, service="backend")
```

#### dyslex_restart
Restart DysLex AI services (stop then start).

**Parameters:**
- `auto_setup` (boolean): Use auto-setup when restarting (default: false)

**Usage:**
```python
dyslex_restart(auto_setup=True)
```

#### dyslex_check
Run prerequisite checks without starting services. Validates Python version, Node.js, PostgreSQL, Redis, dependencies, and ports.

**Usage:**
```python
dyslex_check()
```

### When to Use These Tools

**Use these tools proactively when:**
- Starting work on the project: `dyslex_start(auto_setup=True)`
- User says services aren't working: `dyslex_status()` then diagnose
- User mentions changing backend code: `dyslex_restart()` to reload
- User reports startup issues: `dyslex_check()` to validate environment
- User wants to stop services: `dyslex_stop()`
- Switching between dev and Docker: `dyslex_stop()` then `dyslex_start(mode="docker")`

**Example interactions:**
```
User: "The backend won't start"
→ Run dyslex_check() to see what's wrong
→ If prerequisites fail, suggest dyslex_start(auto_setup=True)
→ If already running, run dyslex_restart()

User: "I updated the API routes"
→ Run dyslex_restart() to reload backend with new code

User: "Start the development server"
→ Run dyslex_start(auto_setup=True) for first-time setup
→ Or dyslex_start() if environment is already configured

User: "Is DysLex AI running?"
→ Run dyslex_status() to show all service statuses
```

### Important Notes

- The MCP server is configured in `~/.claude/mcp_config.json`
- Setup script: `.claude/setup.sh` (already run)
- Full documentation: `.claude/README.md` and `CLAUDE_INTEGRATION.md`
- The tools manage the actual `run.py` script which handles all service orchestration
- Auto-setup mode will: start PostgreSQL/Redis, create backend venv, install dependencies, kill port conflicts
- All services run on localhost by default (backend: 8000, frontend: 3000, PostgreSQL: 5432, Redis: 6379)

---

## Three-Model Architecture

DysLex AI is built from three core models working together. Each model handles a different job, and they pass information between each other to create a system that improves with every use.

### Model 1: User Error Profile (The Adaptive Brain)

**Type**: Statistical / Pattern Database
**Runs**: Server-side (PostgreSQL)
**Job**: Tracks each user's unique error patterns and frequencies

This is not a neural network — it's a structured database that builds a fingerprint of each user's specific dyslexic error patterns. Every person with dyslexia makes different mistakes. This model captures those unique patterns and uses them to make the other two models smarter.

**What It Stores**:
- **Error Frequency Map**: `"becuase" -> "because" (47 times)`, `"teh" -> "the" (112 times)`
- **Error Type Classification**: Letter reversal: 34%, Phonetic substitution: 28%, Homophone confusion: 22%, Omission: 16%
- **Confusion Pairs**: their/there/they're, effect/affect, wich/which/witch
- **Improvement Tracking**: "teh" errors: 15/week → 3/week over 2 months
- **Context Patterns**: Errors increase in longer documents, fewer in familiar topics

**Key Files**:
- `backend/app/core/error_profile.py` — Profile logic
- `backend/app/db/models.py` — Database schema
- `database/schema/init.sql` — PostgreSQL tables

### Model 2: Quick Correction Model (The Fast Local Fixer)

**Type**: Small fine-tuned Language Model (~100M-500M params)
**Runs**: Client-side (ONNX Runtime Web in browser)
**Job**: Instant corrections for known common errors without API calls

A small language model that runs directly on the user's device. It handles the most common corrections instantly — no network latency, no API costs. The model is personalized: it's fine-tuned on each user's Error Profile, so it gets better at catching that specific person's mistakes over time.

**Latency Target**: Under 50ms per correction — must feel instant.

**Key Files**:
- `frontend/src/services/onnxModel.ts` — ONNX inference
- `ml/quick_correction/` — Training and export scripts

### Model 3: Deep Analysis LLM (The Smart Contextual Engine)

**Type**: Large Language Model
**Runs**: Cloud API (NVIDIA NIM) or Self-hosted (Nemotron)
**Job**: Context-aware correction, homophones, real-word errors, explanations

The most powerful part of the system. A large language model that understands the full context of what the user is trying to say. It catches errors that no traditional spell checker can: real-word errors, homophones in wrong context, severely misspelled words where intent must be inferred, and grammar issues specific to dyslexic writing patterns.

**Two-Tier Processing**:
| Tier | Model | When Used | Latency |
|------|-------|-----------|---------|
| Tier 1: Quick | NVIDIA NIM API (Nemotron-3-Nano) or local ONNX | Common errors, known patterns, real-time typing | <500ms |
| Tier 2: Deep | Nemotron-3-Nano-30B-A3B (self-hosted) | Complex real-word errors, full-document analysis, intent inference | 1-5s |

**Key Files**:
- `backend/app/core/llm_orchestrator.py` — Two-tier routing
- `backend/app/core/prompt_builder.py` — Dynamic prompt construction
- `backend/app/services/nim_client.py` — NVIDIA NIM API client
- `backend/app/services/nemotron_client.py` — Deep analysis client

---

## The Adaptive Learning Loop (The Secret Sauce)

This is what makes DysLex AI different from every other tool. **There are no accept/reject buttons. No pop-ups asking the user to make decisions.** The system learns passively by silently observing what the user naturally does as they write.

### Core Principle: Passive Observation

Instead of asking the user to accept or reject corrections:
- Text snapshots taken every 5-10 seconds while actively typing
- Additional snapshot when user pauses for 3+ seconds
- Background diff engine compares snapshots to detect changes
- Every change is a free training signal

### Five Passive Signals The System Captures

| Signal | What Happened | What The Model Learns |
|--------|---------------|----------------------|
| **Self-correction** | User went back and fixed their own error ("teh" → "the") | This is an error they make AND recognize. Catch it earlier next time. |
| **No change over time** | User left a flagged word alone across multiple sessions | Might be intentional (name, slang, technical term). Add to personal dictionary after 3+ occurrences. |
| **Different word entirely** | User rewrote section, word changed unexpectedly ("bark" → "park") | Captures true intent. High-value training data. |
| **Same error repeated** | User writes "becuase" in 5 different documents | High-frequency persistent error. Prioritize in Quick Correction Model. |
| **Error stops appearing** | User used to write "teh" but hasn't in 2+ weeks | They've internalized this. Reduce priority. Note improvement in dashboard. |

### The Full Passive Loop

```
1. USER WRITES — No special actions needed
2. SNAPSHOTS TAKEN — Every 5-10 seconds, plus on pause
3. DIFFS COMPUTED — Background process compares snapshots
4. ERROR PROFILE UPDATES — New errors added, frequencies updated
5. CORRECTIONS IMPROVE — LLM prompt uses updated profile
6. SILENT CORRECTION — Better corrections appear naturally
7. PROGRESS TRACKED — User discovers improvement when they choose to look
```

### Why Passive Learning Is Better

- **Zero cognitive load**: No decisions = focus entirely on writing
- **Zero stigma**: No visible accept/reject buttons on screen
- **Zero friction**: Works like a normal word processor
- **Better data quality**: Natural behavior produces honest training data

**Key Files**:
- `backend/app/core/adaptive_loop.py` — Snapshot processing
- `frontend/src/hooks/usePassiveLearning.ts` — Snapshot diff engine
- `frontend/src/utils/diffEngine.ts` — Word-level diff algorithm

---

## Four Writing Modes

DysLex AI provides four distinct modes that flow naturally from idea capture through to final polish.

### 1. Capture Mode — Voice-to-Thought

Users tap the microphone and speak freely. The AI transcribes in real-time and identifies idea clusters as draggable thought cards. Beyond transcription: identifies key ideas, potential arguments, examples, and emotional tone.

**Key Files**:
- `frontend/src/components/WritingModes/CaptureMode.tsx`
- `frontend/src/hooks/useVoiceInput.ts`
- `backend/app/services/stt_service.py` — faster-whisper integration

### 2. Mind Map Mode — Organize Ideas

Thought cards become a visual mind map. Ideas are clustered by theme. Users can drag, connect, and reorganize. The AI suggests connections ("This example supports that argument") and identifies gaps ("You have a strong intro and conclusion, but the middle needs more support").

**Key Files**:
- `frontend/src/components/WritingModes/MindMapMode.tsx`

### 3. Draft Mode — Scaffolded Writing

Three-column layout: essay scaffold with progress tracking, the main editor with inline corrections and AI coach nudges, and a corrections panel. Passive learning runs silently in the background. The AI builds a writing scaffold: suggested paragraph order, topic sentences for each section, transition phrases.

**Key Files**:
- `frontend/src/components/WritingModes/DraftMode.tsx`
- `frontend/src/components/Editor/Editor.tsx` — TipTap editor
- `frontend/src/components/Panels/CorrectionsPanel.tsx`

### 4. Polish Mode — Review & Refine

Tracked changes view with accept/dismiss controls, readability scoring, and session summary. Uses Tier 2 Nemotron deep analysis for structural and style suggestions. Each suggestion comes with a plain-English explanation.

**Key Files**:
- `frontend/src/components/WritingModes/PolishMode.tsx`
- `frontend/src/hooks/useTextToSpeech.ts` — MagpieTTS read-back

---

## Accessibility Requirements

The interface must look like a normal, modern word processor. **Nobody should be able to tell it's assistive software by looking at someone's screen.** All dyslexia-specific features work invisibly.

### Typography
- **Fonts**: OpenDyslexic, Atkinson Hyperlegible, Lexie Readable as defaults
- **Font size**: 16px minimum, line spacing 1.5-2.0
- **Letter/word spacing**: Slightly increased (0.05-0.12em letter-spacing)

### Color & Contrast
- Avoid pure black (#000) on pure white (#FFF) — use dark gray on off-white/cream
- Multiple background tint options: cream, light blue, light green, gray
- Color for meaning but never as the only indicator — pair with icons/text
- WCAG AA contrast ratios (4.5:1 for normal text)

### Two Themes

**Cream Theme (Default)**:
- `--bg-primary: #FAF6EE` — Main background
- `--bg-editor: #FFFDF8` — Editor canvas
- `--text-primary: #2D2A24` — Body text (warm dark, not pure black)
- `--accent: #E07B4C` — Primary accent (buttons, errors)

**Night Theme**:
- `--bg-primary: #1A1A22` — Dark blue-gray (not pure black)
- `--bg-editor: #1E1E28` — Editor canvas
- `--text-primary: #E8E4DC` — Body text (warm off-white)
- `--accent: #F0935E` — Brighter orange for dark backgrounds

### UI Features
- **Inline corrections**: Subtle colored underlines (not aggressive red)
- **Read-aloud**: Built-in TTS via MagpieTTS — hearing text helps catch errors
- **Focus mode**: Dims everything except current paragraph
- **Progress dashboard**: Private view showing improvement, never deficits

**Key Files**:
- `frontend/src/styles/tokens.css` — Design tokens
- `frontend/src/styles/themes/cream.css`
- `frontend/src/styles/themes/night.css`
- `.claude/rules/frontend/accessibility.md` — A11y rules

---

## Technical Stack

### Frontend
- **React 18** with functional components and hooks
- **TipTap** (ProseMirror-based) for rich text editing
- **TypeScript** with strict mode
- **Vite** for fast development
- **Zustand** for state management
- **ONNX Runtime Web** for local Quick Correction Model

### Backend
- **Python 3.11+**
- **FastAPI** with async endpoints
- **SQLAlchemy 2.0** with async support
- **Alembic** for migrations
- **Pydantic 2.0** for validation

### Database
- **PostgreSQL 15+** for Error Profile storage
- Tables: users, error_profiles, error_logs, confusion_pairs, error_patterns

### External Services (NVIDIA NIM)
- **Nemotron-3-Nano** — Quick corrections via NIM API
- **Nemotron-3-Nano-30B-A3B** — Deep analysis (self-hosted or Brev)
- **MagpieTTS Multilingual** — Text-to-speech
- **faster-whisper** — Speech-to-text

### Deployment
- **Docker Compose** for full stack orchestration
- **Nginx** for production frontend
- **NVIDIA Brev** for cloud GPU hosting (optional)

---

## Code Style

### Frontend (TypeScript/React)
- Functional components with hooks only
- ES modules (import/export), never CommonJS
- Destructure imports: `import { Component } from './module'`
- All components must be accessible (WCAG AA minimum)
- Use design tokens from `styles/tokens.css`

### Backend (Python/FastAPI)
- Type hints required on all functions
- Pydantic models for all request/response schemas
- Repository pattern for database access
- Async endpoints for I/O-bound operations
- Keep routes thin, logic in services/core

### General
- Never interrupt creative flow with popups
- Corrections appear inline, never as dialogs
- All metrics frame improvement positively
- No visible "error counts" — show "words mastered"

---

## Testing

```bash
# Frontend
cd frontend
npm test -- --testPathPattern=<pattern>
npm run type-check
npm run lint

# Backend
cd backend
pytest tests/ -k <test_name>
mypy app/ --ignore-missing-imports
ruff check app/
```

---

## Key Files Reference

### Architecture
- `docs/architecture.md` — System design overview
- `docs/database-schema.md` — ERD and table docs
- `docs/ml-models.md` — ML model documentation

### Frontend Core
- `frontend/src/App.tsx` — Main app with mode switching
- `frontend/src/components/Editor/Editor.tsx` — TipTap editor
- `frontend/src/hooks/usePassiveLearning.ts` — Snapshot diff engine
- `frontend/src/services/correctionService.ts` — Correction orchestration

### Backend Core
- `backend/app/main.py` — FastAPI entry point
- `backend/app/core/llm_orchestrator.py` — Two-tier LLM routing
- `backend/app/core/error_profile.py` — Adaptive learning logic
- `backend/app/core/adaptive_loop.py` — Passive learning processor
- `backend/app/core/prompt_builder.py` — Dynamic prompt construction

### ML
- `ml/quick_correction/` — Local ONNX model
- `ml/confusion_pairs/en.json` — English homophones
- `ml/synthetic_data/patterns/` — Error pattern definitions

### Development Tools
- `run.py` — Unified service launcher (ONE COMMAND to start everything)
- `RUN_PY_GUIDE.md` — Complete launcher documentation
- `RUN_PY_AUTO_SETUP.md` — Auto-setup mode documentation
- `RUN_PY_QUICKREF.md` — Quick command reference
- `.claude/mcp-server-dyslex.py` — MCP server for Claude Code integration
- `.claude/README.md` — MCP server documentation
- `CLAUDE_INTEGRATION.md` — Claude integration overview

---

## Environment Variables

```bash
# Required
NVIDIA_NIM_API_KEY=your-api-key      # For Nemotron, MagpieTTS, faster-whisper
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex

# Optional
VITE_API_URL=http://localhost:8000   # Backend URL for frontend
JWT_SECRET_KEY=change-me             # For authentication
```

---

## The Dynamic Prompt Architecture

The key to making the LLM work well for dyslexic users is the prompt. It's dynamically constructed for each user based on their Error Profile:

```
SYSTEM: You are a writing assistant for a person with dyslexia.
Your job is to identify and correct errors while preserving the
user's voice and intent. Be encouraging, never condescending.

USER ERROR PROFILE (loaded from database):
- Most common errors: [top 20 from error_patterns table]
- Error types: [breakdown from error classification]
- Confusion pairs: [from confusion_pairs table]
- Writing level: [estimated from historical data]

INSTRUCTIONS:
1. Read the full text and understand the intended meaning
2. Identify all errors, prioritizing the user's known patterns
3. For each error, provide: original, correction, error type, brief friendly explanation
4. Flag any real-word errors
5. Return structured JSON for frontend display

USER TEXT: [the text they just wrote]
```

---

## Open Source Commitment

DysLex AI is fully committed to open source under the **Apache 2.0 license**. The entire project — frontend, backend, ML models, Docker config, and documentation — is released so anyone can use, modify, and contribute.

Dyslexia affects roughly 1 in 5 people worldwide. An assistive writing tool this powerful should not be locked behind a paywall. Schools, nonprofits, and individual developers should be able to run it, fork it, translate it, and improve it.

---

## Remember

- **This is an accessibility-first tool** — every feature must work for dyslexic users
- **Passive learning is core** — no accept/reject buttons, learn from behavior
- **The user is intelligent** — they need better tools, not simpler ideas
- **Voice is first-class** — not an afterthought
- **Corrections are invisible** — never interrupt creative flow
- **Show progress, not deficits** — celebrate improvement

### When Working on This Project

- **Use MCP tools proactively** — If the user mentions the services aren't working, run `dyslex_status()` to diagnose
- **Auto-setup is your friend** — When in doubt, use `dyslex_start(auto_setup=True)` to handle prerequisites
- **Check before you code** — Run `dyslex_check()` before implementing fixes to understand the actual state
- **Restart after changes** — When you modify backend code, use `dyslex_restart()` so the user can test immediately
- **One command to rule them all** — Always prefer `python3 run.py --auto-setup` over manual service management

> "Everyone has ideas worth sharing. The right tool just makes sharing them easier."
