# run.py - Unified Launcher Implementation

## Overview

The `run.py` script provides a single command to start, monitor, and stop all DysLex AI services with intelligent prerequisite checking, colored log output, health monitoring, and graceful shutdown.

## Implementation Date

February 6, 2026

## Problem Solved

Previously, developers had to:
1. Start PostgreSQL manually
2. Start Redis manually
3. Open a terminal for backend, activate venv, run uvicorn
4. Open another terminal for frontend, run npm dev
5. Monitor multiple terminal windows
6. Remember to kill all processes when done

This often led to:
- Orphaned processes consuming ports
- Forgetting to start required services
- Confusion about which service produced which log
- Difficulty troubleshooting startup issues

## Solution

A comprehensive Python script that:
1. **Validates prerequisites** before starting anything
2. **Starts all services** with a single command
3. **Multiplexes logs** with colored service prefixes
4. **Monitors health** to confirm services are ready
5. **Handles shutdown** gracefully with no orphaned processes

## Architecture

### Core Components

#### 1. PrerequisiteChecker (~350 lines)
Validates environment before startup:
- Python 3.11+
- Node.js 20+ (dev mode)
- PostgreSQL running on localhost:5432 (dev mode)
- Redis running on localhost:6379 (warning only)
- Docker available (Docker mode)
- Backend virtual environment exists
- Frontend node_modules exists
- Ports 8000 and 3000 are available
- Environment variables present (warning only)

Platform-specific error messages with fix commands for macOS, Linux, and Windows.

#### 2. ServiceManager (~450 lines)
Orchestrates process lifecycle:
- **start_backend()**: Spawns uvicorn with venv Python
- **start_frontend()**: Spawns npm run dev
- **start_docker()**: Spawns docker compose
- **stop_all()**: Graceful shutdown with SIGTERM → SIGKILL fallback

Uses `asyncio.create_subprocess_exec()` for non-blocking process management.

#### 3. LogMultiplexer (~150 lines)
Handles colored, prefixed output:
- Reads stdout/stderr asynchronously from all processes
- Prefixes each line with `[service]` in service-specific color
- Thread-safe output prevents interleaved log lines
- Supports info, success, warning, error levels

Colors:
- `[system]` - White
- `[backend]` - Blue
- `[frontend]` - Magenta
- `[docker]` - Cyan

#### 4. HealthMonitor (~100 lines)
Verifies service readiness:
- **Backend**: Polls `http://localhost:8000/health` until 200 OK (30s timeout)
- **Frontend**: Waits for Vite startup (10s)
- **Docker**: Health check after container startup

#### 5. SignalHandler (~80 lines)
Graceful shutdown:
- Registers handlers for SIGINT (Ctrl+C) and SIGTERM
- Sets asyncio event to trigger shutdown
- Coordinates with ServiceManager to stop all processes

### Process Flow

```
1. Load .env file if present
2. Parse command-line arguments
3. Print startup banner
4. Run prerequisite checks
   ├─ If checks fail: Print errors and exit(1)
   └─ If --check-only: Print results and exit(0)
5. Initialize LogMultiplexer
6. Initialize ServiceManager
7. Set up SignalHandler
8. Start services based on mode
9. Wait for health checks to pass
10. Print ready banner with URLs
11. Wait for shutdown signal (Ctrl+C)
12. Stop all services gracefully
13. Exit cleanly
```

## Features

### Modes

| Mode | Flag | Services Started |
|------|------|------------------|
| Development (default) | none | Backend + Frontend |
| Docker | `--docker` | Docker Compose (all 4 containers) |
| Backend Only | `--backend-only` | FastAPI backend |
| Frontend Only | `--frontend-only` | Vite dev server |
| Check Only | `--check-only` | None (validation only) |

### CLI Options

```bash
--docker                 # Use Docker Compose
--backend-only           # Start only backend
--frontend-only          # Start only frontend
--check-only             # Run checks without starting services
--no-color               # Disable colored output
--skip-checks            # Skip prerequisite checks (dangerous)
--port-backend PORT      # Backend port (default: 8000)
--port-frontend PORT     # Frontend port (default: 3000)
--verbose, -v            # Enable verbose error output
```

### Error Messages

All error messages include:
1. Clear description of what's wrong
2. Platform-specific fix command
3. Helpful context or documentation links

Example:
```
❌ PostgreSQL is not running on localhost:5432
    Fix: Start PostgreSQL: brew services start postgresql@15
```

### Graceful Shutdown

When Ctrl+C is pressed:
1. Signal handler catches SIGINT
2. Shutdown event is set
3. For each process:
   - Send SIGTERM
   - Wait up to 5 seconds for graceful exit
   - Send SIGKILL if still alive
4. Cancel all log streaming tasks
5. Print "Shutdown complete"
6. Exit with code 0

No orphaned processes, no port conflicts on restart.

## File Structure

```
run.py (1,500 lines)
├── Imports & Constants (40 lines)
├── Exception Classes (40 lines)
│   ├── CheckError
│   ├── CheckWarning
│   └── CheckSkipped
├── PrerequisiteChecker (350 lines)
│   ├── check_all()
│   ├── check_python_version()
│   ├── check_node_version()
│   ├── check_postgres_service()
│   ├── check_redis_service()
│   ├── check_environment_variables()
│   ├── check_backend_dependencies()
│   ├── check_frontend_dependencies()
│   ├── check_docker_availability()
│   ├── check_backend_port()
│   ├── check_frontend_port()
│   └── print_results()
├── LogMultiplexer (150 lines)
│   ├── read_stream()
│   ├── log()
│   ├── info()
│   ├── success()
│   ├── warning()
│   └── error()
├── HealthMonitor (100 lines)
│   ├── wait_for_service()
│   └── check_http_endpoint()
├── ServiceManager (450 lines)
│   ├── start_all()
│   ├── start_backend()
│   ├── start_frontend()
│   ├── start_docker()
│   ├── _wait_for_health()
│   ├── stop_all()
│   └── _stop_process()
├── SignalHandler (80 lines)
│   ├── setup()
│   ├── _handle_signal()
│   └── wait_for_shutdown()
├── Utility Functions (150 lines)
│   ├── load_dotenv()
│   ├── print_banner()
│   ├── print_ready_banner()
│   └── create_argument_parser()
└── main() (140 lines)
```

## Dependencies

**None!** The script uses only Python standard library:

- `asyncio` - Async process management
- `subprocess` - Process spawning (via asyncio)
- `signal` - Signal handling
- `argparse` - CLI argument parsing
- `pathlib` - Cross-platform paths
- `socket` - Port checking
- `urllib.request` - HTTP health checks
- `sys`, `os`, `platform`, `time` - System interaction

## Platform Support

### macOS
- Virtual env path: `backend/venv/bin/python`
- PostgreSQL start: `brew services start postgresql@15`
- Redis start: `brew services start redis`

### Linux
- Virtual env path: `backend/venv/bin/python`
- PostgreSQL start: `sudo systemctl start postgresql`
- Redis start: `sudo systemctl start redis`

### Windows
- Virtual env path: `backend\venv\Scripts\python.exe`
- PostgreSQL start: Services panel
- Redis start: Docker or manual install

## Testing

Created `test_run_py.sh` script that validates:
1. Script exists and is executable
2. Help output works
3. Check-only mode works for all modes
4. No-color mode works
5. Custom ports work
6. Python version detection works
7. Node.js version detection works

All tests pass successfully.

## Integration Points

### Backend
- Reads `backend/app/main.py` for lifespan events
- Reads `backend/app/config.py` for default values
- Uses virtual environment at `backend/venv/`
- Monitors health endpoint at `/health`

### Frontend
- Reads `frontend/package.json` for npm scripts
- Checks for `frontend/node_modules/`
- Sets `PORT` environment variable for Vite

### Docker
- Uses `docker/docker-compose.yml`
- Passes through environment variables from host
- Monitors container health

### Environment
- Auto-loads `.env` file from project root
- Reads `NVIDIA_NIM_API_KEY` (warning if missing)
- Reads `DATABASE_URL` (uses default)
- Reads `REDIS_URL` (uses default)

## Documentation

Created comprehensive documentation:

1. **RUN_PY_GUIDE.md** (full user guide)
   - Usage examples
   - Troubleshooting
   - Platform-specific notes
   - Integration with IDEs
   - Environment variables
   - FAQ

2. **README.md** (updated)
   - Added "One-Command Launcher" section
   - Made it the recommended approach
   - Linked to RUN_PY_GUIDE.md

3. **RUN_PY_IMPLEMENTATION.md** (this file)
   - Technical architecture
   - Implementation details
   - File structure
   - Testing approach

## Usage Examples

### Basic Usage
```bash
# Start everything
python3 run.py

# Check prerequisites
python3 run.py --check-only

# Use Docker
python3 run.py --docker

# Backend only
python3 run.py --backend-only

# Custom ports
python3 run.py --port-backend 8080 --port-frontend 3001
```

### Expected Output

```
============================================================
  DysLex AI - Starting in DEV mode
============================================================

✅ All critical checks passed

⚠️  Warnings:
  • Missing environment variables: NVIDIA_NIM_API_KEY
    Fix: Copy docker/.env.example to .env and configure
    Note: Some features (LLM corrections, TTS) will not work without these

[backend] Starting backend on port 8000...
[frontend] Starting frontend on port 3000...
[backend] INFO:     Uvicorn running on http://0.0.0.0:8000
[frontend]   VITE v5.0.0  ready in 1234 ms
[system] Waiting for Backend to be ready...
[system] Backend is ready
[system] Frontend is ready

============================================================
  🚀 DysLex AI is ready!
============================================================
  Frontend: http://localhost:3000
  Backend API: http://localhost:8000
  API Docs: http://localhost:8000/docs

  Press Ctrl+C to stop
============================================================

[backend] INFO:     127.0.0.1:54321 - "GET /health HTTP/1.1" 200 OK
```

### Shutdown Output

```
^C[system] Shutting down...
[backend] Stopping...
[frontend] Stopping...
[backend] Stopped
[frontend] Stopped
[system] Shutdown complete
```

## Success Criteria

All criteria met:

- ✅ Single command starts both backend and frontend
- ✅ All prerequisite checks work with helpful error messages
- ✅ Colored, prefixed logs clearly show service sources
- ✅ Health checks verify services are ready
- ✅ Ctrl+C gracefully shuts down all processes
- ✅ All 4 modes work: dev, docker, backend-only, frontend-only
- ✅ Port conflicts and missing dependencies detected with fixes
- ✅ Works on macOS (tested), Linux, and Windows (cross-platform code)
- ✅ Uses only Python standard library
- ✅ Documentation explains usage and available flags

## Future Enhancements

Potential improvements for future versions:

1. **Watch mode**: Auto-restart services on file changes
2. **Log filtering**: `--filter backend` to show only specific services
3. **Log files**: `--log-dir` to write logs to files
4. **Service dependencies**: Start services in order with dependency graph
5. **Status command**: `python run.py status` to check running services
6. **Stop command**: `python run.py stop` to stop services in another terminal
7. **Daemon mode**: `python run.py --daemon` to run in background
8. **Web dashboard**: Simple HTTP interface to view logs and status
9. **Config file**: `.runpy.yaml` for persistent configuration
10. **Plugin system**: Allow custom checks and services

## Related Files

- `run.py` - Main launcher script
- `RUN_PY_GUIDE.md` - User documentation
- `test_run_py.sh` - Test script
- `README.md` - Updated with launcher section
- `backend/app/main.py` - Backend entry point
- `backend/app/config.py` - Configuration defaults
- `frontend/package.json` - Frontend scripts
- `docker/docker-compose.yml` - Docker configuration
- `docker/.env.example` - Environment template

## Lessons Learned

1. **Standard library is sufficient**: No need for external dependencies (colorama, psutil, etc.) when standard library provides the tools.

2. **Asyncio is excellent for process management**: `asyncio.create_subprocess_exec()` with stream reading is clean and performant.

3. **Platform-specific help is valuable**: Users appreciate commands that work on their OS.

4. **Fail-fast is developer-friendly**: Check everything before starting anything.

5. **Colored output aids debugging**: Service-specific colors make it easy to scan logs.

6. **Graceful shutdown prevents frustration**: No orphaned processes means no port conflicts on restart.

7. **Comprehensive error messages save time**: When a check fails, tell users exactly how to fix it.

8. **Multiple modes increase utility**: Backend-only and frontend-only modes are useful for development workflows.

## Conclusion

The `run.py` unified launcher significantly improves the developer experience for DysLex AI. What previously required 4+ manual steps and multiple terminal windows now works with a single command. The script is robust, cross-platform, well-documented, and requires no external dependencies.

This implementation demonstrates that thoughtful tooling can dramatically reduce cognitive load and make complex systems more accessible to new contributors.
