# Claude Integration for DysLex AI

This directory contains Claude Code integrations for managing DysLex AI services.

## 🔧 MCP Server (Recommended)

The **MCP (Model Context Protocol) Server** provides tools for Claude to control DysLex AI services interactively.

### Features

- ✅ `dyslex_start` - Start services with options
- ✅ `dyslex_stop` - Stop all services gracefully
- ✅ `dyslex_status` - Check service status and health
- ✅ `dyslex_logs` - View recent logs
- ✅ `dyslex_restart` - Restart services
- ✅ `dyslex_check` - Run prerequisite checks

### Setup

1. **Install MCP SDK** (if not already installed):
   ```bash
   pip install mcp
   ```

2. **Add to Claude Code MCP Config**:

   Open or create `~/.claude/mcp_config.json`:
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

3. **Restart Claude Code**

### Usage in Claude Code

Once configured, you can ask Claude to control DysLex AI:

```
You: "Start DysLex AI with auto-setup"
Claude: [Uses dyslex_start tool with auto_setup=true]

You: "Check the status of DysLex AI"
Claude: [Uses dyslex_status tool]

You: "Show me the logs"
Claude: [Uses dyslex_logs tool]

You: "Stop DysLex AI"
Claude: [Uses dyslex_stop tool]
```

### Available Tools

#### dyslex_start

Start DysLex AI services.

**Parameters:**
- `mode` (string): 'dev', 'docker', 'backend', or 'frontend' (default: 'dev')
- `auto_setup` (boolean): Auto-handle prerequisites (default: false)
- `backend_port` (integer): Backend port (default: 8000)
- `frontend_port` (integer): Frontend port (default: 3000)

**Examples:**
```python
# Start with auto-setup
dyslex_start(auto_setup=True)

# Start in Docker mode
dyslex_start(mode="docker")

# Start only backend on custom port
dyslex_start(mode="backend", backend_port=8080)
```

#### dyslex_stop

Stop all DysLex AI services gracefully.

**Parameters:** None

**Example:**
```python
dyslex_stop()
```

#### dyslex_status

Check service status and health.

**Parameters:** None

**Returns:**
- Process status (running/not running)
- Port status for backend, frontend, PostgreSQL, Redis
- Access URLs (if running)

**Example:**
```python
dyslex_status()
```

#### dyslex_logs

View recent logs from services.

**Parameters:**
- `lines` (integer): Number of lines to show (default: 50)
- `service` (string): Filter by service: 'all', 'backend', 'frontend', 'system' (default: 'all')

**Example:**
```python
dyslex_logs(lines=100, service="backend")
```

#### dyslex_restart

Restart DysLex AI services.

**Parameters:**
- `auto_setup` (boolean): Use auto-setup when restarting (default: false)

**Example:**
```python
dyslex_restart(auto_setup=True)
```

#### dyslex_check

Run prerequisite checks without starting services.

**Parameters:** None

**Example:**
```python
dyslex_check()
```

## 🪝 Hooks (Optional)

Hooks allow automatic actions based on events.

### Available Hooks

#### auto-start.sh

Automatically start DysLex AI services on certain triggers.

**Location:** `.claude/hooks/auto-start.sh`

**Configuration:**

Edit the `TRIGGER` variable in the hook:

```bash
TRIGGER="manual"     # Default - no auto-start
TRIGGER="on-enter"   # Auto-start when entering project
```

**Triggers:**
- `manual` - Never auto-start (default)
- `on-enter` - Start when entering project directory
- `on-command` - Start on specific command (not yet implemented)

**Enable auto-start:**

1. Edit `.claude/hooks/auto-start.sh`
2. Change `TRIGGER="manual"` to `TRIGGER="on-enter"`
3. Save the file

Now DysLex AI will auto-start when you open the project in Claude Code!

## 🎯 Quick Examples

### Example 1: Start with Auto-Setup

**In Claude Code:**
```
You: Start DysLex AI with auto-setup
```

**What happens:**
1. Claude calls `dyslex_start(auto_setup=True)`
2. MCP server runs `run.py --auto-setup`
3. PostgreSQL, Redis start automatically
4. Backend venv created if missing
5. Dependencies installed
6. Services start on ports 8000 and 3000

### Example 2: Check Status

**In Claude Code:**
```
You: What's the status of DysLex AI?
```

**What you get:**
```
# DysLex AI Status

✅ Process Running (PID: 12345)

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

### Example 3: Restart After Code Changes

**In Claude Code:**
```
You: I just updated the backend code. Restart DysLex AI.
```

**What happens:**
1. Claude calls `dyslex_restart()`
2. Services stop gracefully
3. Services start again with new code

## 🛠️ Troubleshooting

### MCP Server Not Found

**Problem:** Claude says tools are not available

**Solutions:**
1. Check MCP config: `cat ~/.claude/mcp_config.json`
2. Verify path in config matches: `/Users/connorsecrist/Dyslexia/.claude/mcp-server-dyslex.py`
3. Restart Claude Code
4. Check MCP server works: `python3 .claude/mcp-server-dyslex.py`

### Permission Denied

**Problem:** Can't execute hook or MCP server

**Solution:**
```bash
chmod +x .claude/mcp-server-dyslex.py
chmod +x .claude/hooks/auto-start.sh
```

### Services Already Running

**Problem:** MCP server says services are already running

**Solution:**
1. Use `dyslex_stop` first
2. Or use `dyslex_restart`
3. Or manually: `pkill -f "run.py"`

### Port Conflicts

**Problem:** Ports 8000 or 3000 in use

**Solutions:**
1. Use auto-setup: `dyslex_start(auto_setup=True)`
2. Or custom ports: `dyslex_start(backend_port=8080, frontend_port=3001)`
3. Or kill manually: `lsof -ti :3000 | xargs kill -9`

## 📚 Architecture

### MCP Server Architecture

```
┌─────────────────┐
│  Claude Code    │
│                 │
│  "Start DysLex" │
└────────┬────────┘
         │
         │ MCP Protocol
         │
┌────────▼────────────────┐
│  mcp-server-dyslex.py   │
│                         │
│  Tools:                 │
│  - dyslex_start()       │
│  - dyslex_stop()        │
│  - dyslex_status()      │
│  - dyslex_logs()        │
│  - dyslex_restart()     │
│  - dyslex_check()       │
└────────┬────────────────┘
         │
         │ subprocess
         │
┌────────▼────────┐
│    run.py       │
│                 │
│  - Checks       │
│  - Start svcs   │
│  - Health mon   │
│  - Logs         │
└─────────────────┘
```

### Data Flow

1. **User asks Claude** to control DysLex AI
2. **Claude calls MCP tool** with appropriate parameters
3. **MCP server executes** run.py with correct flags
4. **run.py manages** actual services (backend, frontend, etc.)
5. **MCP server returns** status/output to Claude
6. **Claude shows** formatted response to user

## 🔐 Security

- MCP server runs with user's permissions
- No elevated privileges required
- All services run locally
- No external network access required

## 🚀 Advanced Usage

### Custom MCP Tools

You can extend the MCP server with custom tools. Edit `.claude/mcp-server-dyslex.py`:

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        # ... existing tools ...
        types.Tool(
            name="dyslex_custom",
            description="Your custom tool",
            inputSchema={...}
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "dyslex_custom":
        return await your_custom_function(arguments)
    # ... existing tools ...
```

### Multiple Hooks

Create additional hooks in `.claude/hooks/`:

```bash
.claude/hooks/
├── auto-start.sh         # Auto-start services
├── pre-commit.sh         # Run before commits
├── post-update.sh        # Run after code updates
└── on-file-change.sh     # Run on file changes
```

### Integration with CI/CD

Use the MCP server in CI/CD pipelines:

```bash
# In CI script
python3 .claude/mcp-server-dyslex.py --tool dyslex_check
```

## 📖 Related Documentation

- [run.py Guide](../RUN_PY_GUIDE.md) - Full launcher documentation
- [Auto-Setup Guide](../RUN_PY_AUTO_SETUP.md) - Auto-setup details
- [Quick Reference](../RUN_PY_QUICKREF.md) - Command reference
- [MCP Protocol Docs](https://modelcontextprotocol.io/) - Official MCP docs

## 🤝 Contributing

To improve the MCP server or hooks:

1. Edit the files in `.claude/`
2. Test your changes
3. Update this README
4. Commit with descriptive message

## 📝 License

Same as DysLex AI - Apache 2.0
