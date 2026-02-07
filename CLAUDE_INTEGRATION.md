# DysLex AI Claude Integration

## Overview

This document describes the Claude Code integration for DysLex AI, which allows you to control the entire application stack using natural language commands in Claude Code.

## What We Built

### 1. MCP Server (`.claude/mcp-server-dyslex.py`)

A **Model Context Protocol (MCP) Server** that provides 6 tools for Claude to control DysLex AI:

| Tool | Description | Example |
|------|-------------|---------|
| `dyslex_start` | Start services with options | Start with auto-setup, Docker mode, custom ports |
| `dyslex_stop` | Stop all services gracefully | Stop everything cleanly |
| `dyslex_status` | Check service health | Get status of all services and ports |
| `dyslex_logs` | View recent logs | See what's happening |
| `dyslex_restart` | Restart services | Restart after code changes |
| `dyslex_check` | Run prerequisite checks | Validate environment |

### 2. Auto-Start Hook (`.claude/hooks/auto-start.sh`)

An optional hook that can automatically start DysLex AI when you open the project in Claude Code.

### 3. Setup Script (`.claude/setup.sh`)

A one-command setup script that:
- Installs MCP SDK if needed
- Configures Claude Code MCP settings
- Makes all scripts executable
- Tests the installation

### 4. Documentation (`.claude/README.md`)

Comprehensive documentation covering:
- Setup instructions
- Usage examples
- Tool reference
- Troubleshooting
- Advanced customization

## Quick Start

### Step 1: Run Setup

```bash
cd /Users/connorsecrist/Dyslexia
.claude/setup.sh
```

### Step 2: Restart Claude Code

Close and reopen Claude Code to load the new MCP server.

### Step 3: Use It!

Just ask Claude in natural language:

```
You: "Start DysLex AI with auto-setup"

Claude: [Uses dyslex_start tool]
✅ DysLex AI started in DEV mode with auto-setup

Services are starting up...
Use dyslex_status to check when ready, or dyslex_logs to view progress.

Process ID: 12345
```

## Usage Examples

### Example 1: First Time Setup and Start

**You say:**
```
Start DysLex AI with auto-setup
```

**What happens:**
1. Claude calls `dyslex_start(auto_setup=True)`
2. PostgreSQL and Redis start automatically
3. Backend venv created if missing
4. Dependencies installed
5. Port conflicts resolved
6. Services start on ports 8000 and 3000

**Response:**
```
✅ DysLex AI started in DEV mode with auto-setup

Services are starting up...
Process ID: 45678
```

### Example 2: Check Status

**You say:**
```
What's the status of DysLex AI?
```

**Response:**
```
# DysLex AI Status

✅ Process Running (PID: 45678)

## Services
✅ Backend API (port 8000): Running
✅ Frontend (port 3000): Running
✅ PostgreSQL (port 5432): Running
✅ Redis (port 6379): Running

## URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
```

### Example 3: Stop Services

**You say:**
```
Stop DysLex AI
```

**Response:**
```
✅ DysLex AI stopped gracefully
```

### Example 4: Restart After Code Changes

**You say:**
```
I just updated the backend routes. Restart DysLex AI.
```

**What happens:**
1. Claude calls `dyslex_restart()`
2. Services stop gracefully
3. Wait 2 seconds
4. Services start again with new code

**Response:**
```
🔄 Restarting DysLex AI...

✅ DysLex AI stopped gracefully

✅ DysLex AI started in DEV mode

Services are starting up...
Process ID: 45789
```

### Example 5: Check Prerequisites

**You say:**
```
Check if my environment is ready for DysLex AI
```

**Response:**
```
# Prerequisite Check Results

✅ All critical checks passed

⚠️  Warnings:
  • Missing environment variables: NVIDIA_NIM_API_KEY
    Fix: Copy docker/.env.example to .env and configure
    Note: Some features (LLM corrections, TTS) will not work without these
```

### Example 6: Start in Docker Mode

**You say:**
```
Start DysLex AI in Docker mode
```

**What happens:**
1. Claude calls `dyslex_start(mode="docker")`
2. Docker Compose starts all containers
3. PostgreSQL, Redis, backend, frontend all containerized

**Response:**
```
✅ DysLex AI started in DOCKER mode

Services are starting up...
Process ID: 45890
```

### Example 7: Custom Ports

**You say:**
```
Start DysLex AI backend on port 8080 and frontend on port 3001
```

**What happens:**
1. Claude calls `dyslex_start(backend_port=8080, frontend_port=3001)`
2. Services start on custom ports

**Response:**
```
✅ DysLex AI started in DEV mode

Services are starting up...
Process ID: 45901
```

## Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────┐
│  You (User)                                             │
│  "Start DysLex AI with auto-setup"                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ Natural Language
                         │
┌────────────────────────▼────────────────────────────────┐
│  Claude Code (AI Assistant)                             │
│  - Understands intent                                   │
│  - Selects appropriate tool                             │
│  - Calls: dyslex_start(auto_setup=True)                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ MCP Protocol
                         │
┌────────────────────────▼────────────────────────────────┐
│  MCP Server (mcp-server-dyslex.py)                      │
│  - Receives tool call                                   │
│  - Validates parameters                                 │
│  - Executes: python3 run.py --auto-setup               │
│  - Returns formatted response                           │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ subprocess
                         │
┌────────────────────────▼────────────────────────────────┐
│  run.py (Service Launcher)                              │
│  - Checks prerequisites                                 │
│  - Starts PostgreSQL, Redis                             │
│  - Creates venv, installs deps                          │
│  - Starts backend (FastAPI)                             │
│  - Starts frontend (Vite)                               │
│  - Monitors health                                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         │
┌────────────────────────▼────────────────────────────────┐
│  DysLex AI Services                                     │
│  ✅ Backend API (port 8000)                             │
│  ✅ Frontend App (port 3000)                            │
│  ✅ PostgreSQL (port 5432)                              │
│  ✅ Redis (port 6379)                                   │
└─────────────────────────────────────────────────────────┘
```

## Benefits

### 1. Natural Language Control

Instead of remembering commands:
```bash
cd /Users/connorsecrist/Dyslexia
python3 run.py --auto-setup
```

Just say:
```
Start DysLex AI with auto-setup
```

### 2. Contextual Awareness

Claude knows the state of services and can suggest appropriate actions:

```
You: "I need to test my API changes"
Claude: "Let me restart the backend for you"
[Calls dyslex_restart()]
```

### 3. Error Handling

If something goes wrong, Claude can diagnose and suggest fixes:

```
You: "DysLex AI won't start"
Claude: "Let me check the prerequisites"
[Calls dyslex_check()]
[Sees PostgreSQL is not running]
Claude: "PostgreSQL isn't running. Let me start it with auto-setup"
[Calls dyslex_start(auto_setup=True)]
```

### 4. Documentation Built-In

Ask questions and get instant answers:

```
You: "What ports does DysLex AI use?"
Claude: [Calls dyslex_status()]
"Backend uses port 8000, frontend uses port 3000"
```

### 5. Automation

Enable auto-start hook to have services ready when you start coding:

```bash
# Edit .claude/hooks/auto-start.sh
TRIGGER="on-enter"  # Enable auto-start

# Now when you open the project:
# 🚀 Starting DysLex AI services...
# ✅ Services starting...
```

## Configuration

### MCP Server Configuration

The MCP server is configured in `~/.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "dyslex-ai": {
      "command": "python3",
      "args": [
        "/Users/connorsecrist/Dyslexia/.claude/mcp-server-dyslex.py"
      ],
      "description": "DysLex AI service controller"
    }
  }
}
```

### Hook Configuration

Enable auto-start by editing `.claude/hooks/auto-start.sh`:

```bash
TRIGGER="on-enter"  # Auto-start when entering project
```

## Troubleshooting

### Tools Not Showing Up

**Problem:** Claude says "I don't have access to DysLex AI tools"

**Solutions:**
1. Run setup: `.claude/setup.sh`
2. Check MCP config: `cat ~/.claude/mcp_config.json`
3. Restart Claude Code
4. Verify path matches your system

### MCP Server Errors

**Problem:** "Error executing dyslex_start"

**Solutions:**
1. Test manually: `python3 .claude/mcp-server-dyslex.py`
2. Check permissions: `ls -la .claude/`
3. Verify Python: `python3 --version` (need 3.11+)
4. Check logs in Claude Code console

### Services Won't Start

**Problem:** Services fail to start via MCP

**Solutions:**
1. Try manually: `python3 run.py --check-only`
2. Use auto-setup: Ask Claude to "Start with auto-setup"
3. Check status: Ask Claude "Check DysLex AI status"
4. View logs: Check `/tmp/dyslex-ai.log`

## Extending the Integration

### Add Custom Tools

Edit `.claude/mcp-server-dyslex.py` to add new tools:

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        # Existing tools...
        types.Tool(
            name="dyslex_deploy",
            description="Deploy DysLex AI to production",
            inputSchema={
                "type": "object",
                "properties": {
                    "environment": {
                        "type": "string",
                        "enum": ["staging", "production"]
                    }
                }
            }
        )
    ]
```

### Add Custom Hooks

Create new hooks in `.claude/hooks/`:

```bash
# .claude/hooks/pre-commit.sh
#!/bin/bash
# Run tests before committing
python3 run.py --check-only
```

## Files Created

```
.claude/
├── README.md                    # Full documentation
├── mcp-server-dyslex.py        # MCP server implementation
├── mcp-config.json             # Local MCP config (reference)
├── setup.sh                    # One-command setup script
└── hooks/
    └── auto-start.sh           # Auto-start hook (optional)
```

## Related Documentation

- [.claude/README.md](.claude/README.md) - Detailed MCP server docs
- [RUN_PY_GUIDE.md](RUN_PY_GUIDE.md) - Launcher documentation
- [RUN_PY_AUTO_SETUP.md](RUN_PY_AUTO_SETUP.md) - Auto-setup guide
- [MCP Protocol Docs](https://modelcontextprotocol.io/) - Official MCP documentation

## Summary

The Claude integration makes DysLex AI incredibly easy to manage:

**Before:**
```bash
# Terminal 1
brew services start postgresql@15
brew services start redis
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm install
npm run dev

# Remember all these commands every time!
```

**After:**
```
You: "Start DysLex AI with auto-setup"
Claude: ✅ Done! All services running.
```

That's the power of the Claude integration! 🚀
