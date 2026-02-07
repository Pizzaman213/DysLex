# run.py - Unified DysLex AI Launcher

The `run.py` script provides a single command to start, monitor, and stop all DysLex AI services with intelligent prerequisite checking, colored log output, health monitoring, and graceful shutdown.

## Quick Start

```bash
# Development mode (backend + frontend)
python run.py

# Docker Compose mode
python run.py --docker

# Backend only
python run.py --backend-only

# Frontend only
python run.py --frontend-only

# Check prerequisites without starting
python run.py --check-only
```

## Features

### ✅ Intelligent Prerequisite Checks

Before starting any services, the script validates:

- **Python version**: 3.11+ required
- **Node.js version**: 20+ required (dev mode only)
- **PostgreSQL**: Running on localhost:5432 (dev mode only)
- **Redis**: Running on localhost:6379 (warning only, optional)
- **Docker**: Installed and running (Docker mode only)
- **Backend dependencies**: Virtual environment and packages installed
- **Frontend dependencies**: node_modules installed
- **Port availability**: Checks that ports 8000 and 3000 are available
- **Environment variables**: Warns if NVIDIA_NIM_API_KEY is missing

### 🎨 Colored Log Output

Each service's logs are prefixed with a colored service name:

- `[backend]` - Blue
- `[frontend]` - Magenta
- `[docker]` - Cyan
- `[system]` - White

### 🏥 Health Monitoring

The script waits for services to be ready before showing the success banner:

- **Backend**: Polls `http://localhost:8000/health` until it responds (30s timeout)
- **Frontend**: Waits for Vite dev server to start (10s timeout)
- **Docker**: Checks that all containers are running and healthy

### 🛑 Graceful Shutdown

Press `Ctrl+C` to trigger graceful shutdown:

1. Sends SIGTERM to all processes
2. Waits up to 5 seconds for graceful exit
3. Sends SIGKILL if processes don't terminate
4. Ensures no orphaned processes

## Usage

### Development Mode (Default)

Starts both backend and frontend in parallel:

```bash
python run.py
```

**What it does:**
- Starts FastAPI backend on port 8000 with auto-reload
- Starts Vite frontend dev server on port 3000
- Streams logs from both services with colored prefixes
- Waits for health checks to pass
- Shows ready banner with URLs

**Requirements:**
- PostgreSQL running on localhost:5432
- Redis running on localhost:6379 (optional)
- Backend virtual environment set up
- Frontend node_modules installed

### Docker Compose Mode

Starts the entire stack using Docker:

```bash
python run.py --docker
```

**What it does:**
- Runs `docker compose -f docker/docker-compose.yml up`
- Starts all 4 containers: frontend, backend, PostgreSQL, Redis
- Streams Docker logs with colored prefix
- Waits for services to be healthy

**Requirements:**
- Docker installed and running
- NVIDIA_NIM_API_KEY environment variable set (optional)

### Backend Only Mode

Starts only the FastAPI backend:

```bash
python run.py --backend-only
```

**Useful for:**
- Testing backend API independently
- Frontend development with existing backend
- Running backend tests

### Frontend Only Mode

Starts only the Vite frontend dev server:

```bash
python run.py --frontend-only
```

**Useful for:**
- Frontend development with existing backend
- Testing UI components independently
- Running frontend tests

### Check Only Mode

Runs prerequisite checks without starting services:

```bash
python run.py --check-only
```

**Useful for:**
- Validating environment setup
- Troubleshooting startup issues
- CI/CD environment validation

## Command-Line Options

### Mode Selection (Mutually Exclusive)

```bash
--docker              # Use Docker Compose
--backend-only        # Run only backend
--frontend-only       # Run only frontend
# (default is dev mode: backend + frontend)
```

### Configuration Options

```bash
--port-backend PORT   # Backend port (default: 8000)
--port-frontend PORT  # Frontend port (default: 3000)
--no-color            # Disable colored output
--skip-checks         # Skip prerequisite checks (dangerous)
--verbose, -v         # Enable verbose error output
--check-only          # Run checks only, don't start services
```

## Examples

### Custom Ports

```bash
python run.py --port-backend 8080 --port-frontend 3001
```

### Backend Only with Custom Port

```bash
python run.py --backend-only --port-backend 8080
```

### Check Environment Without Starting

```bash
python run.py --check-only
```

### Docker Mode with Verbose Output

```bash
python run.py --docker --verbose
```

### Disable Colors (for CI/CD)

```bash
python run.py --no-color
```

## Troubleshooting

### Port Already in Use

**Error:**
```
❌ Port 8000 is already in use
    Fix: Stop the existing process or use --port-backend <port>
```

**Solution:**
1. Find the process: `lsof -i :8000`
2. Kill it: `kill -9 <PID>`
3. Or use a different port: `python run.py --port-backend 8080`

### PostgreSQL Not Running

**Error (macOS):**
```
❌ PostgreSQL is not running on localhost:5432
    Fix: Start PostgreSQL: brew services start postgresql@15
```

**Solutions:**
- **macOS**: `brew services start postgresql@15`
- **Linux**: `sudo systemctl start postgresql`
- **Windows**: Start via Services panel
- **All**: Use Docker mode: `python run.py --docker`

### Redis Not Running

**Warning:**
```
⚠️  Redis is not running on localhost:6379
    Fix: Start Redis: brew services start redis
    Note: Redis is optional but recommended for snapshot storage
```

**Impact:** Non-critical. The app will work but snapshot caching will be disabled.

**Solutions:**
- **macOS**: `brew services start redis`
- **Linux**: `sudo systemctl start redis`
- **Windows**: Use Docker: `python run.py --docker`
- **All**: Ignore warning and continue (snapshots will work without Redis)

### Missing Environment Variables

**Warning:**
```
⚠️  Missing environment variables: NVIDIA_NIM_API_KEY
    Fix: Copy docker/.env.example to .env and configure
    Note: Some features (LLM corrections, TTS) will not work without these
```

**Impact:** LLM-powered features (corrections, TTS) won't work.

**Solution:**
1. Copy template: `cp docker/.env.example .env`
2. Edit `.env` and add your NVIDIA NIM API key
3. Restart: `python run.py`

### Backend Dependencies Missing

**Error:**
```
❌ Backend virtual environment not found
    Fix: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

**Solution:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
python run.py
```

### Frontend Dependencies Missing

**Error:**
```
❌ Frontend dependencies not installed
    Fix: cd frontend && npm install
```

**Solution:**
```bash
cd frontend
npm install
cd ..
python run.py
```

### Docker Not Running

**Error:**
```
❌ Docker daemon is not running
    Fix: Start Docker Desktop
```

**Solution:**
1. Open Docker Desktop
2. Wait for it to start
3. Retry: `python run.py --docker`

### Health Check Timeout

**Error:**
```
[system] Backend failed to start within 30s
```

**Possible causes:**
1. Backend crashed on startup (check logs above)
2. Database connection failed (check PostgreSQL)
3. Port conflict (check if 8000 is in use)
4. Missing dependencies (check virtual environment)

**Solution:**
1. Review the backend logs in the output
2. Check prerequisites: `python run.py --check-only`
3. Try backend only: `python run.py --backend-only`
4. Check backend logs directly: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`

## Platform-Specific Notes

### macOS

- PostgreSQL: `brew services start postgresql@15`
- Redis: `brew services start redis`
- Virtual env path: `backend/venv/bin/python`

### Linux

- PostgreSQL: `sudo systemctl start postgresql`
- Redis: `sudo systemctl start redis`
- Virtual env path: `backend/venv/bin/python`

### Windows

- PostgreSQL: Start via Services panel
- Redis: Download from redis.io or use Docker
- Virtual env path: `backend\venv\Scripts\python.exe`

## Integration with Development Workflow

### With Claude Code

```bash
# In Claude Code with Chrome integration
claude --chrome
# Then run this in the terminal
python run.py
# Navigate to localhost:3000 in the Chrome instance
```

### With VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start DysLex AI",
      "type": "shell",
      "command": "python run.py",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    }
  ]
}
```

Then: `Cmd+Shift+P` → "Tasks: Run Task" → "Start DysLex AI"

### With tmux

```bash
# Create a new tmux session
tmux new -s dyslex

# Start the launcher
python run.py

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t dyslex
# Kill: tmux kill-session -t dyslex
```

## Environment Variables

The script automatically loads `.env` from the project root if it exists.

**Required:**
- `DATABASE_URL` - PostgreSQL connection string (defaults to local)
- `NVIDIA_NIM_API_KEY` - NVIDIA NIM API key (warning if missing)

**Optional:**
- `REDIS_URL` - Redis connection string (defaults to local)
- `JWT_SECRET_KEY` - JWT signing key (defaults to insecure value)

**Example `.env`:**
```bash
NVIDIA_NIM_API_KEY=your-api-key-here
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-me-in-production
```

## Exit Codes

- `0` - Success (normal exit or Ctrl+C)
- `1` - Prerequisite checks failed
- `1` - Fatal error during startup

## Technical Details

### Process Management

- Uses `asyncio.create_subprocess_exec()` for non-blocking process spawning
- Streams stdout/stderr asynchronously with line buffering
- Thread-safe log multiplexing prevents interleaved output

### Health Checks

- **Backend**: HTTP GET to `/health` endpoint, expects 200 OK
- **Frontend**: Waits for Vite dev server startup (time-based)
- **Docker**: HTTP check after container startup delay

### Graceful Shutdown

1. SIGINT/SIGTERM handler sets shutdown event
2. ServiceManager sends SIGTERM to each child process
3. Waits up to 5 seconds for each process to exit
4. Sends SIGKILL to any remaining processes
5. Cancels all asyncio log streaming tasks

### Virtual Environment Detection

Automatically finds the backend Python:
1. Try `backend/venv/bin/python` (Unix)
2. Fall back to `backend/venv/Scripts/python.exe` (Windows)

## FAQ

**Q: Can I run multiple instances?**
A: Yes, but use different ports: `python run.py --port-backend 8001 --port-frontend 3001`

**Q: Does this work in CI/CD?**
A: Yes! Use `--no-color` and `--check-only` for validation.

**Q: Can I skip checks?**
A: Yes with `--skip-checks`, but not recommended. Only use if you know what you're doing.

**Q: How do I see just backend logs?**
A: Use `python run.py --backend-only` or redirect: `python run.py 2>&1 | grep "\[backend\]"`

**Q: What if I need to restart just one service?**
A: Use the individual modes (`--backend-only` or `--frontend-only`) in separate terminals.

**Q: Does this replace Docker Compose?**
A: No, it provides both options. Use `--docker` for containerized deployment, or default mode for faster development iteration.

## Related Documentation

- [MODULE_9_SETUP.md](MODULE_9_SETUP.md) - Full setup guide
- [CLAUDE.md](CLAUDE.md) - Project philosophy and architecture
- [docker/docker-compose.yml](docker/docker-compose.yml) - Docker configuration
- [backend/app/main.py](backend/app/main.py) - Backend entry point
- [frontend/package.json](frontend/package.json) - Frontend scripts

## Contributing

If you find issues or have suggestions for improving the launcher:

1. Check existing issues: https://github.com/anthropics/dyslex-ai/issues
2. Open a new issue with:
   - Your platform (macOS/Linux/Windows)
   - Python version (`python --version`)
   - Node version (`node --version`)
   - Full error output
   - Steps to reproduce

## License

Apache 2.0 - See [LICENSE](LICENSE) file.
