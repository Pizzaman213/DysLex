#!/usr/bin/env python3
"""
DysLex AI MCP Server

Provides tools for Claude to control DysLex AI services.

Tools:
- dyslex_start: Start DysLex AI services
- dyslex_stop: Stop DysLex AI services
- dyslex_status: Check service status
- dyslex_logs: View recent logs
- dyslex_restart: Restart services
"""

import asyncio
import base64
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# MCP SDK imports
try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
RUN_SCRIPT = PROJECT_ROOT / "run.py"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Global state
server = Server("dyslex-ai")
dyslex_process: Optional[subprocess.Popen] = None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="dyslex_start",
            description="Start DysLex AI services (backend + frontend). Optionally use --auto-setup to handle prerequisites automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Start mode: 'dev' (default), 'docker', 'backend', or 'frontend'",
                        "enum": ["dev", "docker", "backend", "frontend"],
                        "default": "dev"
                    },
                    "auto_setup": {
                        "type": "boolean",
                        "description": "Automatically start PostgreSQL, Redis, create venv, install deps, kill port conflicts",
                        "default": False
                    },
                    "backend_port": {
                        "type": "integer",
                        "description": "Backend port (default: 8000)",
                        "default": 8000
                    },
                    "frontend_port": {
                        "type": "integer",
                        "description": "Frontend port (default: 3000)",
                        "default": 3000
                    }
                }
            }
        ),
        types.Tool(
            name="dyslex_stop",
            description="Stop all DysLex AI services gracefully",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="dyslex_status",
            description="Check if DysLex AI services are running and get service status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="dyslex_logs",
            description="View recent logs from DysLex AI services",
            inputSchema={
                "type": "object",
                "properties": {
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines to show (default: 50)",
                        "default": 50
                    },
                    "service": {
                        "type": "string",
                        "description": "Filter logs by service: 'all' (default), 'backend', 'frontend', 'system'",
                        "enum": ["all", "backend", "frontend", "system"],
                        "default": "all"
                    }
                }
            }
        ),
        types.Tool(
            name="dyslex_restart",
            description="Restart DysLex AI services (stop then start)",
            inputSchema={
                "type": "object",
                "properties": {
                    "auto_setup": {
                        "type": "boolean",
                        "description": "Use auto-setup when restarting",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="dyslex_check",
            description="Run prerequisite checks without starting services",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="dyslex_screenshot",
            description="Take a screenshot of the DysLex AI frontend using headless Chrome. Returns the image so Claude can visually inspect the UI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to screenshot (default: http://localhost:3000)",
                        "default": "http://localhost:3000"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Viewport width in pixels (default: 1280)",
                        "default": 1280
                    },
                    "height": {
                        "type": "integer",
                        "description": "Viewport height in pixels (default: 900)",
                        "default": 900
                    },
                    "wait": {
                        "type": "integer",
                        "description": "Milliseconds to wait for page to render (default: 3000)",
                        "default": 3000
                    },
                    "full_page": {
                        "type": "boolean",
                        "description": "Capture the full scrollable page instead of just the viewport (default: false)",
                        "default": False
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""
    global dyslex_process

    if not arguments:
        arguments = {}

    try:
        if name == "dyslex_start":
            return await start_dyslex(arguments)
        elif name == "dyslex_stop":
            return await stop_dyslex()
        elif name == "dyslex_status":
            return await get_status()
        elif name == "dyslex_logs":
            return await get_logs(arguments)
        elif name == "dyslex_restart":
            return await restart_dyslex(arguments)
        elif name == "dyslex_check":
            return await check_prerequisites()
        elif name == "dyslex_screenshot":
            return await take_screenshot(arguments)
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def start_dyslex(args: dict) -> list[types.TextContent]:
    """Start DysLex AI services."""
    global dyslex_process

    # Check if already running
    if dyslex_process and dyslex_process.poll() is None:
        return [types.TextContent(
            type="text",
            text="❌ DysLex AI is already running. Use dyslex_stop first, or dyslex_restart to restart."
        )]

    # Build command
    cmd = [sys.executable, str(RUN_SCRIPT)]

    mode = args.get("mode", "dev")
    if mode == "docker":
        cmd.append("--docker")
    elif mode == "backend":
        cmd.append("--backend-only")
    elif mode == "frontend":
        cmd.append("--frontend-only")

    if args.get("auto_setup", False):
        cmd.append("--auto-setup")

    if args.get("backend_port"):
        cmd.extend(["--port-backend", str(args["backend_port"])])

    if args.get("frontend_port"):
        cmd.extend(["--port-frontend", str(args["frontend_port"])])

    # Start the process
    try:
        dyslex_process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Wait a moment for startup
        await asyncio.sleep(2)

        # Check if it started successfully
        if dyslex_process.poll() is not None:
            # Process exited
            output = dyslex_process.stdout.read() if dyslex_process.stdout else "No output"
            return [types.TextContent(
                type="text",
                text=f"❌ Failed to start DysLex AI\n\nOutput:\n{output}"
            )]

        mode_str = mode.upper()
        auto_str = " with auto-setup" if args.get("auto_setup") else ""

        return [types.TextContent(
            type="text",
            text=f"✅ DysLex AI started in {mode_str} mode{auto_str}\n\n"
                 f"Services are starting up...\n"
                 f"Use dyslex_status to check when ready, or dyslex_logs to view progress.\n\n"
                 f"Process ID: {dyslex_process.pid}"
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Error starting DysLex AI: {str(e)}"
        )]


async def stop_dyslex() -> list[types.TextContent]:
    """Stop DysLex AI services."""
    global dyslex_process

    if not dyslex_process or dyslex_process.poll() is not None:
        return [types.TextContent(
            type="text",
            text="ℹ️  DysLex AI is not running"
        )]

    try:
        # Send SIGTERM for graceful shutdown
        dyslex_process.terminate()

        # Wait up to 10 seconds for graceful shutdown
        try:
            dyslex_process.wait(timeout=10)
            return [types.TextContent(
                type="text",
                text="✅ DysLex AI stopped gracefully"
            )]
        except subprocess.TimeoutExpired:
            # Force kill if still running
            dyslex_process.kill()
            dyslex_process.wait()
            return [types.TextContent(
                type="text",
                text="⚠️  DysLex AI force stopped (graceful shutdown timed out)"
            )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Error stopping DysLex AI: {str(e)}"
        )]


async def get_status() -> list[types.TextContent]:
    """Get service status."""
    global dyslex_process

    # Check process status
    process_running = dyslex_process and dyslex_process.poll() is None

    status_lines = ["# DysLex AI Status\n"]

    if process_running:
        status_lines.append(f"✅ **Process Running** (PID: {dyslex_process.pid})\n")
    else:
        status_lines.append("❌ **Process Not Running**\n")

    # Check ports
    import socket

    def check_port(port: int, name: str) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    return f"✅ {name} (port {port}): **Running**"
                else:
                    return f"❌ {name} (port {port}): Not responding"
        except Exception as e:
            return f"⚠️  {name} (port {port}): Error checking ({str(e)})"

    status_lines.append("\n## Services\n")
    status_lines.append(check_port(8000, "Backend API"))
    status_lines.append(check_port(3000, "Frontend"))
    status_lines.append(check_port(5432, "PostgreSQL"))
    status_lines.append(check_port(6379, "Redis"))

    # URLs
    if process_running:
        status_lines.append("\n## URLs\n")
        status_lines.append("- Frontend: http://localhost:3000")
        status_lines.append("- Backend API: http://localhost:8000")
        status_lines.append("- API Docs: http://localhost:8000/docs")

    return [types.TextContent(
        type="text",
        text="\n".join(status_lines)
    )]


async def get_logs(args: dict) -> list[types.TextContent]:
    """Get recent logs."""
    global dyslex_process

    if not dyslex_process or dyslex_process.poll() is not None:
        return [types.TextContent(
            type="text",
            text="ℹ️  DysLex AI is not running. No logs available."
        )]

    lines = args.get("lines", 50)
    service_filter = args.get("service", "all")

    # Note: This is a simplified implementation
    # In a real implementation, you'd want to capture and store logs properly

    return [types.TextContent(
        type="text",
        text=f"📝 Log viewing not yet implemented in this version.\n\n"
             f"To view logs, use:\n"
             f"- Check the terminal where DysLex AI is running\n"
             f"- Or use: tail -f /path/to/log/file\n\n"
             f"The process is running with PID: {dyslex_process.pid}"
    )]


async def restart_dyslex(args: dict) -> list[types.TextContent]:
    """Restart DysLex AI services."""
    # Stop first
    stop_result = await stop_dyslex()

    # Wait a moment
    await asyncio.sleep(2)

    # Start again
    start_result = await start_dyslex(args)

    return [
        types.TextContent(
            type="text",
            text="🔄 Restarting DysLex AI...\n\n"
        )
    ] + stop_result + [
        types.TextContent(type="text", text="\n")
    ] + start_result


async def check_prerequisites() -> list[types.TextContent]:
    """Run prerequisite checks."""
    try:
        result = subprocess.run(
            [sys.executable, str(RUN_SCRIPT), "--check-only"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )

        return [types.TextContent(
            type="text",
            text=f"# Prerequisite Check Results\n\n```\n{result.stdout}\n```"
        )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Error checking prerequisites: {str(e)}"
        )]


async def take_screenshot(args: dict) -> list[types.TextContent | types.ImageContent]:
    """Take a screenshot of the frontend using headless Chrome."""
    url = args.get("url", "http://localhost:3000")
    width = args.get("width", 1280)
    height = args.get("height", 900)
    wait_ms = args.get("wait", 3000)
    full_page = args.get("full_page", False)

    if not Path(CHROME_PATH).exists():
        return [types.TextContent(
            type="text",
            text="Google Chrome not found at expected path. Install Chrome to use screenshots."
        )]

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        screenshot_path = tmp.name

    try:
        cmd = [
            CHROME_PATH,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            f"--screenshot={screenshot_path}",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={wait_ms}",
        ]

        if full_page:
            cmd.append("--full-page-screenshot")

        cmd.append(url)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        screenshot_file = Path(screenshot_path)
        if not screenshot_file.exists() or screenshot_file.stat().st_size == 0:
            return [types.TextContent(
                type="text",
                text=f"Screenshot failed. Chrome stderr:\n{result.stderr[:1000]}"
            )]

        image_data = base64.b64encode(screenshot_file.read_bytes()).decode("utf-8")
        screenshot_file.unlink()

        return [
            types.ImageContent(
                type="image",
                data=image_data,
                mimeType="image/png"
            ),
            types.TextContent(
                type="text",
                text=f"Screenshot of {url} ({width}x{height})"
            )
        ]

    except subprocess.TimeoutExpired:
        Path(screenshot_path).unlink(missing_ok=True)
        return [types.TextContent(
            type="text",
            text="Screenshot timed out after 30 seconds."
        )]
    except Exception as e:
        Path(screenshot_path).unlink(missing_ok=True)
        return [types.TextContent(
            type="text",
            text=f"Screenshot error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dyslex-ai",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
