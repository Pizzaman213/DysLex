# run.py Enhancement: --auto-setup Mode

## What Changed

Enhanced `run.py` to automatically handle common development environment setup issues instead of just checking and reporting them.

## New Flags

### `--auto-setup`
Automatically fixes environment issues:
- Starts PostgreSQL if not running (macOS/Linux)
- Starts Redis if not running (macOS/Linux)
- Creates backend virtual environment if missing
- Installs Python dependencies automatically
- Kills processes on conflicting ports
- Stops auto-started services on shutdown

### `--kill-ports`
Only handles port conflicts (without starting services):
- Kills processes on ports 8000 and 3000
- Useful when you just need to free ports

## Before and After

### Before (Manual)
```bash
$ python3 run.py

❌ Prerequisite checks failed:
  • PostgreSQL is not running on localhost:5432
    Fix: Start PostgreSQL: brew services start postgresql@15
  • Backend virtual environment not found
    Fix: cd backend && python -m venv venv && ...
  • Port 3000 is already in use
    Fix: Stop the existing process or use --port-frontend <port>

# User has to manually:
$ brew services start postgresql@15
$ cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
$ lsof -ti :3000 | xargs kill -9
$ python3 run.py  # Finally works
```

### After (Automatic)
```bash
$ python3 run.py --auto-setup

⚙️  Starting PostgreSQL...
✓ PostgreSQL started

⚙️  Creating backend virtual environment...
  Creating virtual environment...
  Installing dependencies (this may take a few minutes)...
✓ Backend venv created and dependencies installed

⚙️  Killing process on port 3000...
✓ Port 3000 freed

✅ All critical checks passed

[backend] Starting backend on port 8000...
[frontend] Starting frontend on port 3000...

============================================================
  🚀 DysLex AI is ready!
============================================================
```

## Implementation Details

### New Methods in PrerequisiteChecker

1. **`_start_postgres()`** - Starts PostgreSQL via brew services (macOS) or systemctl (Linux)
2. **`_start_redis()`** - Starts Redis via brew services (macOS) or systemctl (Linux)
3. **`_create_backend_venv()`** - Creates venv and runs pip install
4. **`_kill_port_process(port)`** - Finds and kills process using specified port
5. **`cleanup_started_services()`** - Stops services that were auto-started
6. **`_stop_postgres()`** - Stops PostgreSQL
7. **`_stop_redis()`** - Stops Redis

### Modified Check Methods

Updated these methods to call fix methods when `auto_setup=True`:
- `check_postgres_service()` - Calls `_start_postgres()` if not running
- `check_redis_service()` - Calls `_start_redis()` if not running
- `check_backend_dependencies()` - Calls `_create_backend_venv()` if missing
- `check_backend_port()` - Calls `_kill_port_process()` if port in use
- `check_frontend_port()` - Calls `_kill_port_process()` if port in use

### Service Tracking

The checker tracks which services it started in `self.services_started` list. On shutdown, only these services are stopped, preventing interference with services that were already running.

### Platform Support

| Platform | PostgreSQL | Redis | Venv | Port Kill |
|----------|------------|-------|------|-----------|
| macOS | ✅ Homebrew | ✅ Homebrew | ✅ Yes | ✅ lsof |
| Linux | ✅ systemctl | ✅ systemctl | ✅ Yes | ✅ lsof |
| Windows | ❌ No | ❌ No | ✅ Yes | ✅ netstat |

## Usage Examples

### First-Time Setup
```bash
# Clone repo
git clone https://github.com/yourusername/dyslexia.git
cd dyslexia

# Install frontend deps (one-time)
cd frontend && npm install && cd ..

# Start with auto-setup
python3 run.py --auto-setup
```

### Daily Development
```bash
# If services are running
python3 run.py

# If you need a clean start
python3 run.py --auto-setup
```

### Port Conflicts Only
```bash
# Just free ports without starting services
python3 run.py --kill-ports
```

### Check What Would Be Fixed
```bash
# See what auto-setup would do without actually doing it
python3 run.py --check-only

# Then run with auto-setup
python3 run.py --auto-setup
```

## Graceful Cleanup

When you press Ctrl+C, the script:

1. Stops backend and frontend processes
2. Checks if any services were auto-started
3. Stops those services (PostgreSQL, Redis)
4. Prints confirmation

Example output:
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

## Error Handling

If auto-setup fails for any component, you get a clear error message:

```bash
❌ Prerequisite checks failed:

  • Failed to start PostgreSQL automatically
    Fix: Start PostgreSQL: brew services start postgresql@15

  • Failed to create backend virtual environment
    Fix: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

Fix the issues above and try again.
```

The script will:
1. Not start any services (fail-fast)
2. Exit with code 1
3. Show manual fix commands

## Documentation Updates

Created/updated these files:

1. **RUN_PY_AUTO_SETUP.md** - Comprehensive guide to auto-setup mode
2. **RUN_PY_QUICKREF.md** - Updated with new flags and examples
3. **README.md** - Highlighted auto-setup as recommended approach
4. **RUN_PY_ENHANCEMENTS.md** - This file

## Testing

Tested on macOS with various scenarios:

✅ PostgreSQL not running → auto-started successfully
✅ Redis not running → auto-started successfully
✅ Backend venv missing → created and deps installed
✅ Port 3000 in use → process killed successfully
✅ Graceful shutdown → auto-started services stopped
✅ Services already running → detected and skipped
✅ Mixed conditions → handled correctly

## Limitations

1. **Frontend dependencies** - NOT auto-installed (npm install is slow, can fail)
2. **Windows services** - Limited support (use Docker mode instead)
3. **Custom PostgreSQL versions** - May not detect non-standard installations
4. **Root-owned processes** - Cannot kill processes owned by root
5. **Database initialization** - Doesn't create databases or run migrations

## Benefits

1. **Faster onboarding** - New developers can start with one command
2. **Fewer errors** - Common issues are fixed automatically
3. **Less cognitive load** - Don't need to remember all setup steps
4. **Cleaner shutdown** - Auto-started services are stopped properly
5. **Better DX** - Development experience matches the project's philosophy

## Philosophy Alignment

This enhancement aligns with DysLex AI's core principle:

> "The goal isn't to fix how someone writes — it's to free the ideas already inside them."

Applied to developer experience:

> "The goal isn't to teach developers all the setup steps — it's to free them to focus on building features."

Just like DysLex AI removes friction from writing, `--auto-setup` removes friction from development.

## Future Enhancements

Potential improvements:

1. **Database initialization** - Automatically run migrations on first start
2. **Frontend npm install** - Auto-install with progress indicator
3. **Config validation** - Check .env file and offer to create from template
4. **Service health monitoring** - Restart services if they crash
5. **Dependency updates** - Detect outdated dependencies and offer to update
6. **macOS app bundle** - Package as .app for non-technical users
7. **GUI mode** - Simple graphical interface for service management

## Conclusion

The `--auto-setup` flag transforms DysLex AI from a project that requires careful manual setup into one that "just works" with a single command. This dramatically improves the developer experience and lowers the barrier to contribution.

**Before:** 5-10 manual steps, multiple terminal windows, easy to forget steps
**After:** One command, automatic setup, clean shutdown

This is the kind of polish that makes open-source projects more accessible and enjoyable to work with.
