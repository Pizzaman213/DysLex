# run.py --auto-setup: One-Command Development Environment

## Overview

The `--auto-setup` flag transforms `run.py` from a service launcher into a comprehensive development environment manager. Instead of manually starting PostgreSQL, Redis, creating virtual environments, and managing port conflicts, a single command handles everything automatically.

## What It Does

### Before --auto-setup (Manual Process)

```bash
# 1. Start PostgreSQL
brew services start postgresql@15

# 2. Start Redis
brew services start redis

# 3. Create backend venv
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# 4. Kill port conflicts
lsof -ti :3000 | xargs kill -9

# 5. Finally, start services
python3 run.py
```

### After --auto-setup (One Command)

```bash
python3 run.py --auto-setup
```

That's it. Everything else happens automatically.

## Automatic Actions

When you run `python3 run.py --auto-setup`, the script performs these actions:

### 1. PostgreSQL Management ✅

**Checks:**
- Is PostgreSQL running on localhost:5432?

**Actions if not running:**
- **macOS**: Runs `brew services start postgresql@15`
- **Linux**: Runs `sudo systemctl start postgresql`
- **Windows**: Shows error (use Docker mode instead)
- Waits 3 seconds for service to start
- Verifies connection to port 5432
- Tracks that it was auto-started for cleanup

**Cleanup on shutdown:**
- Stops PostgreSQL if it was auto-started
- **macOS**: Runs `brew services stop postgresql@15`
- **Linux**: Runs `sudo systemctl stop postgresql`

### 2. Redis Management ✅

**Checks:**
- Is Redis running on localhost:6379?

**Actions if not running:**
- **macOS**: Runs `brew services start redis`
- **Linux**: Runs `sudo systemctl start redis`
- **Windows**: Shows warning (optional service)
- Waits 2 seconds for service to start
- Verifies connection to port 6379
- Tracks that it was auto-started for cleanup

**Cleanup on shutdown:**
- Stops Redis if it was auto-started
- **macOS**: Runs `brew services stop redis`
- **Linux**: Runs `sudo systemctl stop redis`

### 3. Backend Virtual Environment ✅

**Checks:**
- Does `backend/venv/bin/python` exist? (Unix)
- Does `backend/venv/Scripts/python.exe` exist? (Windows)

**Actions if not found:**
- Runs `python3 -m venv venv` in backend directory
- Waits 1 second for venv to be created
- Locates pip in the new venv
- Runs `pip install -r requirements.txt`
- Shows installation progress (may take 3-5 minutes)
- Verifies installation succeeded

### 4. Port Conflict Resolution ✅

**Checks:**
- Is port 8000 available? (backend)
- Is port 3000 available? (frontend)

**Actions if port in use:**
- **macOS/Linux**: Runs `lsof -ti :<port>` to find process ID
- **Windows**: Runs `netstat -ano | findstr :<port>` to find process ID
- Kills process with `kill -9 <pid>` (Unix) or `taskkill /F /PID <pid>` (Windows)
- Waits 1 second for port to be freed
- Verifies port is now available

### 5. Frontend Dependencies ⚠️

**Note:** Frontend dependencies (`npm install`) are NOT automatically installed because:
- Takes 1-2 minutes to run
- Can fail if Node.js version is incompatible
- Users should run `cd frontend && npm install` once manually

**Checks:**
- Does `frontend/node_modules` directory exist?
- If missing, shows error with manual fix command

## Output Example

```bash
$ python3 run.py --auto-setup

============================================================
  DysLex AI - Starting in DEV mode
============================================================

⚙️  Starting PostgreSQL...
✓ PostgreSQL started

⚙️  Starting Redis...
✓ Redis started

⚙️  Creating backend virtual environment...
  Creating virtual environment...
  Installing dependencies (this may take a few minutes)...
✓ Backend venv created and dependencies installed

⚙️  Killing process on port 3000...
✓ Port 3000 freed

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
```

## Graceful Cleanup

When you press `Ctrl+C`, the script performs these cleanup steps:

```bash
^C
[system] Shutting down...
[backend] Stopping...
[frontend] Stopping...
[backend] Stopped
[frontend] Stopped
[system] Shutdown complete

Stopping auto-started services...
✓ PostgreSQL stopped
✓ Redis stopped
```

## Platform Support

| Platform | PostgreSQL | Redis | Venv | Port Killing | Recommended |
|----------|------------|-------|------|--------------|-------------|
| macOS | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **Use --auto-setup** |
| Linux | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **Use --auto-setup** |
| Windows | ❌ No | ❌ No | ✅ Yes | ✅ Yes | **Use --docker** |

### macOS Requirements

- Homebrew installed
- PostgreSQL installed via Homebrew: `brew install postgresql@15`
- Redis installed via Homebrew: `brew install redis`

### Linux Requirements

- systemd available
- PostgreSQL installed: `sudo apt install postgresql` or `sudo yum install postgresql-server`
- Redis installed: `sudo apt install redis-server` or `sudo yum install redis`
- May require sudo password for systemctl commands

### Windows Limitations

Windows doesn't have standardized service management like macOS (Homebrew) or Linux (systemd). Instead:
- Use Docker mode: `python3 run.py --docker`
- Or manually start PostgreSQL/Redis via Services panel

## Alternative: --kill-ports Only

If you only want automatic port conflict resolution without auto-starting services:

```bash
python3 run.py --kill-ports
```

This will:
- ✅ Kill processes on ports 8000 and 3000
- ❌ Will NOT start PostgreSQL/Redis
- ❌ Will NOT create backend venv

## Error Handling

If auto-setup fails, you'll see clear error messages:

```bash
❌ Prerequisite checks failed:

  • Failed to start PostgreSQL automatically
    Fix: Start PostgreSQL: brew services start postgresql@15

  • Failed to create backend virtual environment
    Fix: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

The script will:
1. Show what failed
2. Provide the manual fix command
3. Exit with code 1 (no services started)

## Security Considerations

### Service Auto-Start

- **PostgreSQL/Redis**: Only starts if they're installed and configured
- **No sudo**: Never runs commands as root without user awareness (Linux systemctl may prompt for password)
- **Local only**: Only manages services on localhost

### Port Killing

- **Targeted**: Only kills processes on specific ports (8000, 3000)
- **No confirmation**: Kills immediately (use with caution if other apps use these ports)
- **Alternative**: Use custom ports if you need to preserve existing processes: `--port-backend 8080`

### Virtual Environment

- **Isolated**: Creates a clean Python environment in `backend/venv/`
- **No system changes**: Doesn't modify system Python or global packages
- **Safe**: Uses `python3 -m venv` (standard library)

## Troubleshooting

### "Failed to start PostgreSQL automatically"

**Possible causes:**
1. PostgreSQL not installed via Homebrew (macOS)
2. PostgreSQL not installed via package manager (Linux)
3. Different PostgreSQL version (not @15)

**Solutions:**
```bash
# macOS - Install PostgreSQL
brew install postgresql@15

# Linux - Install PostgreSQL
sudo apt install postgresql  # Debian/Ubuntu
sudo yum install postgresql-server  # RHEL/CentOS

# Or skip auto-start
brew services start postgresql@15  # Start manually
python3 run.py  # Run without --auto-setup
```

### "Failed to create backend virtual environment"

**Possible causes:**
1. No write permissions in `backend/` directory
2. Python venv module not installed
3. Disk space full

**Solutions:**
```bash
# Check permissions
ls -la backend/

# Manually create venv
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### "Port could not be freed"

**Possible causes:**
1. Process is protected (owned by root)
2. Process immediately respawns
3. Multiple processes on same port

**Solutions:**
```bash
# Find what's using the port
lsof -i :3000

# Kill manually
kill -9 <PID>

# Or use different port
python3 run.py --port-frontend 3001
```

### PostgreSQL won't stop on cleanup

**Possible causes:**
1. Other applications are using it
2. Script lost track of auto-start status

**Solutions:**
```bash
# Check PostgreSQL status
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Stop manually if needed
brew services stop postgresql@15  # macOS
sudo systemctl stop postgresql  # Linux
```

## Best Practices

### 1. First Time Setup

```bash
# Clone repo
git clone https://github.com/yourusername/dyslexia.git
cd dyslexia

# Install frontend deps (one-time, manual)
cd frontend && npm install && cd ..

# Set up environment variables (optional)
cp docker/.env.example .env
# Edit .env and add NVIDIA_NIM_API_KEY

# Start with auto-setup
python3 run.py --auto-setup
```

### 2. Daily Development

```bash
# If services are already running (PostgreSQL, Redis)
python3 run.py

# If you need a fresh start
python3 run.py --auto-setup
```

### 3. Quick Testing

```bash
# Check environment without starting
python3 run.py --check-only

# Fix issues automatically
python3 run.py --auto-setup --check-only
```

### 4. CI/CD Pipelines

```bash
# Don't use --auto-setup in CI/CD
# Services should be managed by CI environment
python3 run.py --skip-checks --no-color
```

## Comparison with Docker Mode

| Feature | --auto-setup | --docker |
|---------|-------------|----------|
| Setup speed | Fast (if services installed) | Slow (downloads images) |
| Disk space | ~500MB (venv) | ~2GB (Docker images) |
| Hot reload | ✅ Instant | ⚠️  Requires rebuild |
| PostgreSQL | Uses local installation | Fresh container |
| Redis | Uses local installation | Fresh container |
| Port conflicts | Auto-resolves | Uses dedicated ports |
| Platform support | macOS, Linux | All platforms |
| Best for | **Daily development** | **First-time setup** |

## FAQ

**Q: Will this delete my existing data?**
A: No. It only starts/stops services. Your PostgreSQL data, Redis cache, and code are untouched.

**Q: What if I already have PostgreSQL running?**
A: The script detects it's running and skips the auto-start. No changes are made.

**Q: Will it stop PostgreSQL even if I didn't start it?**
A: No. The script tracks what IT started and only stops those services. If PostgreSQL was already running when you started the script, it won't be stopped on shutdown.

**Q: Can I use --auto-setup with custom ports?**
A: Yes! `python3 run.py --auto-setup --port-backend 8080 --port-frontend 3001`

**Q: Is it safe to kill ports automatically?**
A: Generally yes, but be aware it will kill ANY process on ports 8000/3000. If you're running other apps on these ports, use custom ports instead.

**Q: Why doesn't it install frontend dependencies (npm install)?**
A: npm install can take 1-2 minutes and fail for various reasons. It's better to run it once manually: `cd frontend && npm install`

**Q: Can I use this in production?**
A: No. --auto-setup is for development only. Use Docker Compose or proper deployment tools for production.

## Related Documentation

- [RUN_PY_GUIDE.md](RUN_PY_GUIDE.md) - Full user guide
- [RUN_PY_QUICKREF.md](RUN_PY_QUICKREF.md) - Quick reference
- [RUN_PY_IMPLEMENTATION.md](RUN_PY_IMPLEMENTATION.md) - Technical implementation
- [MODULE_9_SETUP.md](MODULE_9_SETUP.md) - Module 9 setup guide

## Summary

The `--auto-setup` flag makes DysLex AI development truly one-command:

✅ No more "PostgreSQL is not running" errors
✅ No more "Port 3000 is already in use" frustration
✅ No more forgetting to create the backend venv
✅ Everything starts automatically and cleans up on shutdown

**Just run: `python3 run.py --auto-setup`**
