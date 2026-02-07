# run.py Quick Reference

## Most Common Commands

```bash
# Auto-setup everything and start (ONE COMMAND!) ⭐
python3 run.py --auto-setup

# Start everything (after manual setup)
python3 run.py

# Check if your environment is set up correctly
python3 run.py --check-only

# Use Docker (easiest for first-time setup)
python3 run.py --docker
```

## All Modes

| Command | What It Does |
|---------|--------------|
| `python3 run.py` | Start backend + frontend |
| `python3 run.py --docker` | Start with Docker Compose |
| `python3 run.py --backend-only` | Start only backend API |
| `python3 run.py --frontend-only` | Start only frontend dev server |
| `python3 run.py --check-only` | Check prerequisites without starting |

## Common Options

| Option | What It Does |
|--------|--------------|
| `--auto-setup` | 🌟 Auto-start PostgreSQL, Redis, create venv, kill port conflicts |
| `--kill-ports` | Automatically kill processes using required ports |
| `--port-backend 8080` | Use custom backend port |
| `--port-frontend 3001` | Use custom frontend port |
| `--no-color` | Disable colored output |
| `--verbose` | Show detailed error messages |
| `--help` | Show all options |

## Auto-Setup Mode (NEW!) ⭐

The `--auto-setup` flag automatically handles common setup issues:

**What it does:**
- ✅ Starts PostgreSQL if not running (macOS/Linux only)
- ✅ Starts Redis if not running (macOS/Linux only)
- ✅ Creates backend virtual environment if missing
- ✅ Installs Python dependencies automatically
- ✅ Kills processes on conflicting ports (8000, 3000)
- ✅ Cleans up auto-started services on shutdown

**Usage:**
```bash
# First time setup (or after a clean checkout)
python3 run.py --auto-setup

# On shutdown (Ctrl+C), it will:
# - Stop backend and frontend
# - Stop PostgreSQL if it was auto-started
# - Stop Redis if it was auto-started
```

**Platform support:**
- ✅ macOS (via Homebrew)
- ✅ Linux (via systemctl)
- ⚠️  Windows (use Docker mode instead)

## Examples

```bash
# Auto-setup and start (one command for everything!)
python3 run.py --auto-setup

# Use different ports (when default ports are busy)
python3 run.py --port-backend 8080 --port-frontend 3001

# Backend only (useful when frontend is already running)
python3 run.py --backend-only

# Frontend only (useful when backend is already running)
python3 run.py --frontend-only

# Docker with verbose output (for troubleshooting)
python3 run.py --docker --verbose

# Check environment for CI/CD
python3 run.py --check-only --no-color
```

## What You'll See When Ready

```
============================================================
  🚀 DysLex AI is ready!
============================================================
  Frontend: http://localhost:3000
  Backend API: http://localhost:8000
  API Docs: http://localhost:8000/docs

  Press Ctrl+C to stop
============================================================
```

## How to Stop

**Press `Ctrl+C`** - All services will shut down cleanly.

## Common Issues

### "Port 8000 is already in use"
**Fix:** `lsof -i :8000` to find the process, then `kill <PID>`, or use `--port-backend 8080`

### "PostgreSQL is not running"
**Fix:** `brew services start postgresql@15` (macOS) or use `--docker` mode

### "Backend virtual environment not found"
**Fix:** `cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`

### "Frontend dependencies not installed"
**Fix:** `cd frontend && npm install`

## Environment Setup (One-Time)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/dyslexia.git
cd dyslexia

# 2. Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 3. Set up frontend
cd frontend
npm install
cd ..

# 4. Set up environment variables
cp docker/.env.example .env
# Edit .env and add your NVIDIA_NIM_API_KEY

# 5. Start PostgreSQL (if not using Docker)
brew services start postgresql@15  # macOS
# OR
sudo systemctl start postgresql     # Linux

# 6. Create database (if not using Docker)
createdb dyslex
psql dyslex < database/schema/init.sql

# 7. Run!
python3 run.py
```

## Or Just Use Docker

```bash
# Skip all setup steps above
python3 run.py --docker
```

Docker will:
- Start PostgreSQL automatically
- Start Redis automatically
- Build and start backend
- Build and start frontend
- Initialize database schema
- Handle all networking

## URLs When Running

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | The main DysLex AI web app |
| Backend API | http://localhost:8000 | REST API server |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API docs |
| Health Check | http://localhost:8000/health | Backend health status |

## Service Colors in Logs

- **[system]** - White - Launcher messages
- **[backend]** - Blue - FastAPI backend
- **[frontend]** - Magenta - Vite dev server
- **[docker]** - Cyan - Docker Compose

## Getting Help

```bash
# Show all options
python3 run.py --help

# Read the full guide
cat RUN_PY_GUIDE.md

# Check the implementation docs
cat RUN_PY_IMPLEMENTATION.md
```

## Tips

1. **Always run `--check-only` first** when setting up a new environment
2. **Use Docker mode** for the simplest experience
3. **Use dev mode** for fastest development iteration (no container rebuilds)
4. **Use backend-only/frontend-only** when working on one side of the stack
5. **Watch the colored logs** to see which service has issues
6. **Press Ctrl+C once** and wait for graceful shutdown (don't spam it!)

---

For full documentation, see [RUN_PY_GUIDE.md](RUN_PY_GUIDE.md)
