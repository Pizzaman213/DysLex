# Module 9 Setup Guide

This guide covers how to set up Module 9's infrastructure: the MCP server, Claude Code hooks, and service management. For verifying individual features (ONNX, TTS, snapshots), see [Module 9 Quick Start](docs/MODULE_9_QUICK_START.md). For technical implementation details, see [Module 9 Implementation Summary](docs/MODULE_9_IMPLEMENTATION_SUMMARY.md).

---

## Overview

Module 9 adds a services and hooks layer that lets you manage DysLex AI directly from Claude Code:

- **MCP Server** — 7 tools (`dyslex_start`, `dyslex_stop`, `dyslex_status`, `dyslex_logs`, `dyslex_restart`, `dyslex_check`, `dyslex_screenshot`) callable from Claude Code
- **Hooks** — 5 optional shell scripts that automate formatting, linting, testing, type-checking, and auto-starting services
- **Unified Launcher** — `run.py` orchestrates all services (backend, frontend, PostgreSQL, Redis) with a single command

---

## Prerequisites

| Requirement | Minimum Version | Check Command |
|-------------|----------------|---------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| PostgreSQL | 15+ | `psql --version` |
| Redis | 7+ | `redis-server --version` |
| npm | 9+ | `npm --version` |

Optional:
- **MCP SDK** — `pip install mcp` (the setup script installs this automatically)
- **NVIDIA NIM API key** — Required for cloud-based Nemotron corrections

---

## 1. Starting Services

The fastest way to get everything running:

```bash
python3 run.py --auto-setup
```

This single command:
- Starts PostgreSQL if not running
- Starts Redis if not running
- Creates the backend virtual environment
- Installs Python dependencies
- Kills processes on conflicting ports (8000, 3000)
- Starts the backend (port 8000) and frontend (port 3000)

After the first run, you can use the shorter form:

```bash
python3 run.py
```

To check prerequisites without starting anything:

```bash
python3 run.py --check-only
```

---

## 2. MCP Server Setup

The MCP server lets Claude Code control DysLex AI services through natural language commands.

### Automated Setup

Run the setup script:

```bash
.claude/setup.sh
```

This script:
1. Installs the MCP SDK (`pip install mcp`) if missing
2. Creates `~/.claude/mcp_config.json` with the DysLex AI server config
3. Makes the MCP server and hooks executable
4. Verifies the installation

### Manual Setup

If you prefer to configure manually:

1. Install the MCP SDK:
   ```bash
   pip install mcp
   ```

2. The project already includes `.mcp.json` at the project root:
   ```json
   {
     "mcpServers": {
       "dyslex-ai": {
         "command": "python3",
         "args": [
           "/Users/connorsecrist/Dyslexia/.claude/mcp-server-dyslex.py"
         ]
       }
     }
   }
   ```

3. Restart Claude Code to load the MCP server.

### Verifying MCP Tools

After restarting Claude Code, test by asking:

```
"Check DysLex AI status"       → triggers dyslex_status
"Start DysLex AI"              → triggers dyslex_start
"Show me the backend logs"     → triggers dyslex_logs
"Take a screenshot"            → triggers dyslex_screenshot
```

If tools aren't available, check:
- `.mcp.json` exists at the project root with the correct path
- The MCP server is executable: `chmod +x .claude/mcp-server-dyslex.py`
- Claude Code has been restarted after config changes

---

## 3. Hooks Setup

Hooks are optional shell scripts in `.claude/hooks/` that run automatically in response to file edits. Each hook reads the edited file path from stdin and runs the appropriate tool.

### Available Hooks

| Hook | File | What It Does | Triggers On |
|------|------|-------------|-------------|
| **Auto-Start** | `auto-start.sh` | Starts DysLex AI services when entering the project | Project open (when enabled) |
| **Format Code** | `format-code.sh` | Runs Prettier (TS/JS) or Ruff (Python) on saved files | `.ts`, `.tsx`, `.js`, `.py` file edits |
| **Lint Check** | `lint-check.sh` | Runs ESLint (TS/JS) or Ruff check (Python) on saved files | `.ts`, `.tsx`, `.js`, `.py` file edits |
| **Run Tests** | `run-tests.sh` | Runs matching test suite for edited files | `frontend/*.ts*`, `backend/*.py` file edits |
| **Type Check** | `typecheck.sh` | Runs `tsc --noEmit` (TS) or `mypy` (Python) | `.ts`, `.tsx`, `.py` file edits |

### Enabling Auto-Start

The auto-start hook is disabled by default. To enable it:

1. Open `.claude/hooks/auto-start.sh`
2. Change `TRIGGER="manual"` to `TRIGGER="on-enter"`
3. Save the file

Now DysLex AI services will start automatically when you open the project in Claude Code.

### Making Hooks Executable

All hooks must be executable to work:

```bash
chmod +x .claude/hooks/*.sh
```

The setup script (`.claude/setup.sh`) handles this automatically.

### How Hooks Work

Each hook (except `auto-start.sh`) reads JSON from stdin containing the tool input, extracts the file path, and runs the appropriate tool based on file extension. For example, `format-code.sh`:

- `.ts` / `.tsx` / `.js` files → `npx prettier --write`
- `.py` files → `python -m ruff format`

Hooks exit with code 0 even if the tool is not applicable, so they never block your workflow.

---

## 4. Verification Checklist

After completing setup, verify each component:

- [ ] **Services start** — `python3 run.py --auto-setup` completes without errors
- [ ] **Frontend accessible** — Open http://localhost:3000
- [ ] **Backend accessible** — Open http://localhost:8000/docs (Swagger UI)
- [ ] **MCP tools work** — Ask Claude Code "Check DysLex AI status"
- [ ] **Hooks executable** — `ls -la .claude/hooks/` shows execute permissions

---

## 5. Troubleshooting

### Port Conflicts

**Symptom:** "Address already in use" on port 8000 or 3000.

**Fix:** Use auto-setup (it kills conflicting processes automatically):
```bash
python3 run.py --auto-setup
```

Or manually find and kill the process:
```bash
lsof -ti :8000 | xargs kill
lsof -ti :3000 | xargs kill
```

Or start on different ports:
```bash
python3 run.py --backend-port 8080 --frontend-port 3001
```

### MCP Server Not Found

**Symptom:** Claude Code says tools are not available.

**Fix:**
1. Verify `.mcp.json` exists at the project root
2. Check the path inside `.mcp.json` points to the correct absolute path
3. Ensure the server is executable: `chmod +x .claude/mcp-server-dyslex.py`
4. Restart Claude Code

### Permission Denied on Hooks

**Symptom:** Hooks don't run or produce "permission denied" errors.

**Fix:**
```bash
chmod +x .claude/hooks/*.sh
```

### Services Already Running

**Symptom:** Start command says services are already running.

**Fix:**
1. Use the MCP tool: ask Claude Code to "Restart DysLex AI"
2. Or stop first: `pkill -f "run.py"`, then start again
3. Or use `dyslex_restart` MCP tool

### PostgreSQL or Redis Not Starting

**Symptom:** `run.py` fails with database connection errors.

**Fix:**
```bash
# macOS (Homebrew)
brew services start postgresql@15
brew services start redis

# Verify
pg_isready
redis-cli ping
```

---

## Related Documentation

- [Module 9 Command Reference](MODULE_9_COMMANDS.md) — Copy-paste command cheat sheet
- [Module 9 Implementation Summary](docs/MODULE_9_IMPLEMENTATION_SUMMARY.md) — Technical details
- [Module 9 Quick Start](docs/MODULE_9_QUICK_START.md) — Feature verification walkthrough
- [MCP Server Documentation](.claude/README.md) — Full MCP server docs
