# DysLex AI

Intelligent writing assistance for dyslexic users. DysLex AI provides real-time, personalized spelling and grammar corrections that learn from your unique patterns.

## Features

- **Adaptive Learning** - The system learns your specific error patterns without explicit feedback
- **Four Writing Modes** - Capture (voice), Mind Map, Draft, and Polish
- **Dyslexia-Friendly UI** - OpenDyslexic font, high contrast themes, no distracting popups
- **Voice Support** - Speech-to-text input and text-to-speech playback
- **Inline Corrections** - Suggestions appear naturally in the text, not as intrusive dialogs

## Architecture

DysLex AI uses a three-model approach:

1. **Error Profile Model** (PostgreSQL) - Stores your personal error patterns
2. **Quick Correction Model** (ONNX) - Fast, local corrections for common errors
3. **Deep Analysis Model** (Nemotron) - Cloud-based analysis for complex grammar

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+
- NVIDIA NIM API key (for Nemotron)

### One-Command Launcher (Recommended) ⭐

```bash
# Auto-setup EVERYTHING and start (best for first time!)
python3 run.py --auto-setup

# After initial setup, just run:
python3 run.py

# Or use Docker Compose mode
python3 run.py --docker

# Check prerequisites without starting
python3 run.py --check-only
```

**What `--auto-setup` does:**
- ✅ Starts PostgreSQL if not running
- ✅ Starts Redis if not running
- ✅ Creates backend virtual environment
- ✅ Installs Python dependencies
- ✅ Kills processes on conflicting ports
- ✅ Cleans up on shutdown

See [RUN_PY_GUIDE.md](RUN_PY_GUIDE.md) for full documentation or [RUN_PY_AUTO_SETUP.md](RUN_PY_AUTO_SETUP.md) for auto-setup details.

### Claude Code Integration 🤖

Control DysLex AI directly from Claude Code using MCP tools:

```bash
# One-time setup
.claude/setup.sh

# Then in Claude Code, just ask:
"Start DysLex AI with auto-setup"
"Check DysLex AI status"
"Show me the logs"
"Restart DysLex AI"
```

See [.claude/README.md](.claude/README.md) for full MCP server documentation.

### Manual Setup

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Database
createdb dyslex
psql dyslex < database/schema/init.sql
```

### Docker

```bash
docker compose -f docker/docker-compose.yml up
```

## Documentation

### Setup & Implementation
- [Module 9 Setup Guide](MODULE_9_SETUP.md) - **Start Here** for Services & Hooks setup
- [Module 9 Command Reference](MODULE_9_COMMANDS.md) - Quick command cheat sheet
- [Module 9 Implementation Summary](docs/MODULE_9_IMPLEMENTATION_SUMMARY.md) - Technical details

### Architecture & Design
- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Database Schema](docs/database-schema.md)
- [ML Models](docs/ml-models.md)
- [Deployment](docs/deployment.md)
- [Contributing](docs/contributing.md)

## Tech Stack

- **Frontend**: React, TipTap, TypeScript, Vite, ONNX Runtime Web
- **Backend**: Python, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **ML**: NVIDIA NIM (Nemotron), MagpieTTS, faster-whisper
- **Infrastructure**: Docker, Nginx

## License

Apache 2.0 - See [LICENSE](LICENSE)
