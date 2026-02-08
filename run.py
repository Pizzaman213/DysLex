#!/usr/bin/env python3
"""
DysLex AI - Unified Development Launcher

A comprehensive script to start, monitor, and stop all DysLex AI services with a single command.
Supports development mode, Docker mode, and individual service modes with intelligent prerequisite
checking, colored log output, health monitoring, and graceful shutdown.

Usage:
    python run.py                    # Development mode (backend + frontend)
    python run.py --host 0.0.0.0     # Network accessible (other devices can connect)
    python run.py --docker           # Docker Compose mode
    python run.py --backend-only     # Backend only
    python run.py --frontend-only    # Frontend only
    python run.py --check-only       # Run checks without starting services

Requirements:
    - Python 3.11+
    - Node.js 20+
    - PostgreSQL 15+ (localhost:5432)
    - Redis (localhost:6379) - optional, warning only
    - Docker (for --docker mode)

Environment Variables:
    - NVIDIA_NIM_API_KEY: Required for LLM/TTS services (warning only)
    - DATABASE_URL: Defaults to postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex
    - REDIS_URL: Defaults to redis://localhost:6379/0

Platform Support:
    - macOS, Linux, Windows

License:
    Apache 2.0 - See LICENSE file
"""

import asyncio
import argparse
import ssl
import sys
import os
import signal
import socket
import subprocess
import platform
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError


# ============================================================================
# Constants
# ============================================================================

PYTHON_MIN_VERSION = (3, 11)
NODE_MIN_VERSION = (20, 0)

DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
DEFAULT_HOST = '0.0.0.0'
POSTGRES_PORT = 5432
REDIS_PORT = 6379

BACKEND_HEALTH_ENDPOINT = "{protocol}://localhost:{port}/health"  # Always check via localhost
BACKEND_STARTUP_TIMEOUT = 30  # seconds
FRONTEND_STARTUP_TIMEOUT = 10  # seconds
HEALTH_CHECK_INTERVAL = 1  # seconds

SHUTDOWN_TIMEOUT = 5  # seconds to wait for graceful shutdown

# ANSI color codes
class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'


# ============================================================================
# Exception Classes
# ============================================================================

class CheckError(Exception):
    """Critical check failure that prevents startup."""
    pass


class CheckWarning(Exception):
    """Non-critical check failure that allows startup with warning."""
    pass


class CheckSkipped(Exception):
    """Check was skipped (e.g., not applicable for current mode)."""
    pass


# ============================================================================
# PrerequisiteChecker
# ============================================================================

class PrerequisiteChecker:
    """Validates environment prerequisites before starting services."""

    def __init__(self, mode: str, config: Dict[str, Any], color_enabled: bool = True):
        self.mode = mode
        self.config = config
        self.color_enabled = color_enabled
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        self.platform_name = platform.system()
        self.auto_setup = config.get('auto_setup', False)
        self.kill_ports = config.get('kill_ports', False)
        self.services_started: List[str] = []  # Track what we started

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    def check_all(self) -> bool:
        """Run all applicable checks. Returns True if all critical checks pass."""
        checks = [
            ("Python version", self.check_python_version),
        ]

        if self.mode == 'docker':
            checks.append(("Docker availability", self.check_docker_availability))
        else:
            # Development mode checks
            if self.mode in ['dev', 'backend']:
                checks.extend([
                    ("PostgreSQL service", self.check_postgres_service),
                    ("Redis service", self.check_redis_service),
                    ("Backend dependencies", self.check_backend_dependencies),
                    ("Backend port availability", self.check_backend_port),
                ])

            if self.mode in ['dev', 'frontend']:
                checks.extend([
                    ("Node.js version", self.check_node_version),
                    ("Frontend dependencies", self.check_frontend_dependencies),
                    ("Frontend port availability", self.check_frontend_port),
                ])

        # Environment variables (warning only)
        checks.append(("Environment variables", self.check_environment_variables))

        # Run all checks
        for name, check_func in checks:
            try:
                check_func()
            except CheckError as e:
                self.errors.append((name, str(e)))
            except CheckWarning as e:
                self.warnings.append((name, str(e)))
            except CheckSkipped:
                pass

        return len(self.errors) == 0

    def check_python_version(self):
        """Verify Python version is 3.11+."""
        version = sys.version_info[:2]
        if version < PYTHON_MIN_VERSION:
            raise CheckError(
                f"Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ required, found {version[0]}.{version[1]}\n"
                f"    Fix: Install Python 3.11+: https://python.org/downloads"
            )

    def check_node_version(self):
        """Verify Node.js version is 20+."""
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_str = result.stdout.strip().lstrip('v')
            major = int(version_str.split('.')[0])

            if major < NODE_MIN_VERSION[0]:
                raise CheckError(
                    f"Node.js {NODE_MIN_VERSION[0]}+ required, found {major}\n"
                    f"    Fix: Install Node.js 20+: https://nodejs.org"
                )
        except FileNotFoundError:
            raise CheckError(
                "Node.js not found\n"
                "    Fix: Install Node.js 20+: https://nodejs.org"
            )
        except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
            raise CheckError(f"Could not determine Node.js version: {e}")

    def check_postgres_service(self):
        """Check if PostgreSQL is running on localhost:5432."""
        if not self._is_port_open('localhost', POSTGRES_PORT):
            if self.auto_setup:
                print(f"{self._colorize('⚙️  Starting PostgreSQL...', Color.YELLOW)}")
                if self._start_postgres():
                    print(f"{self._colorize('✓ PostgreSQL started', Color.GREEN)}")
                    self.services_started.append('postgresql')
                    return
                else:
                    fix_cmd = self._get_postgres_start_command()
                    raise CheckError(
                        f"Failed to start PostgreSQL automatically\n"
                        f"    Fix: {fix_cmd}"
                    )
            else:
                fix_cmd = self._get_postgres_start_command()
                raise CheckError(
                    f"PostgreSQL is not running on localhost:{POSTGRES_PORT}\n"
                    f"    Fix: {fix_cmd}\n"
                    f"    Or use: python3 run.py --auto-setup"
                )

    def check_redis_service(self):
        """Check if Redis is running on localhost:6379 (warning only)."""
        if not self._is_port_open('localhost', REDIS_PORT):
            if self.auto_setup:
                print(f"{self._colorize('⚙️  Starting Redis...', Color.YELLOW)}")
                if self._start_redis():
                    print(f"{self._colorize('✓ Redis started', Color.GREEN)}")
                    self.services_started.append('redis')
                    return
                else:
                    fix_cmd = self._get_redis_start_command()
                    raise CheckWarning(
                        f"Failed to start Redis automatically\n"
                        f"    Fix: {fix_cmd}\n"
                        f"    Note: Redis is optional but recommended for snapshot storage"
                    )
            else:
                fix_cmd = self._get_redis_start_command()
                raise CheckWarning(
                    f"Redis is not running on localhost:{REDIS_PORT}\n"
                    f"    Fix: {fix_cmd}\n"
                    f"    Note: Redis is optional but recommended for snapshot storage\n"
                    f"    Or use: python3 run.py --auto-setup"
                )

    def check_environment_variables(self):
        """Check for required environment variables, prompt if missing."""
        if not os.getenv('NVIDIA_NIM_API_KEY'):
            print(f"\n{self._colorize('🔑 NVIDIA_NIM_API_KEY is not set.', Color.YELLOW)}")
            print(f"   Some features (LLM corrections, TTS) require this key.")
            try:
                key = input(f"   Enter your API key (or press Enter to skip): ").strip()
            except (EOFError, KeyboardInterrupt):
                key = ""
            if key:
                os.environ['NVIDIA_NIM_API_KEY'] = key
                # Save to .env so it persists across restarts
                env_file = Path('.env')
                lines = []
                if env_file.exists():
                    lines = env_file.read_text().splitlines()
                # Replace existing key or append
                found = False
                for i, line in enumerate(lines):
                    if line.strip().startswith('NVIDIA_NIM_API_KEY='):
                        lines[i] = f'NVIDIA_NIM_API_KEY={key}'
                        found = True
                        break
                if not found:
                    lines.append(f'NVIDIA_NIM_API_KEY={key}')
                env_file.write_text('\n'.join(lines) + '\n')
                print(f"   {self._colorize('✓ API key saved to .env', Color.GREEN)}")
            else:
                raise CheckWarning(
                    "NVIDIA_NIM_API_KEY not set (skipped)\n"
                    "    Note: Some features (LLM corrections, TTS) will not work without it"
                )

    def check_backend_dependencies(self):
        """Verify backend virtual environment and dependencies are installed."""
        backend_dir = Path('backend')
        venv_python = self._find_venv_python()

        if not venv_python or not venv_python.exists():
            if self.auto_setup:
                print(f"{self._colorize('⚙️  Creating backend virtual environment...', Color.YELLOW)}")
                if self._create_backend_venv():
                    print(f"{self._colorize('✓ Backend venv created and dependencies installed', Color.GREEN)}")
                    return
                else:
                    raise CheckError(
                        "Failed to create backend virtual environment\n"
                        f"    Fix: cd backend && python3 -m venv venv && {self._get_activate_command()} && pip install -r requirements.txt"
                    )
            else:
                raise CheckError(
                    "Backend virtual environment not found\n"
                    f"    Fix: cd backend && python3 -m venv venv && {self._get_activate_command()} && pip install -r requirements.txt\n"
                    f"    Or use: python3 run.py --auto-setup"
                )

        requirements_file = backend_dir / 'requirements.txt'
        if not requirements_file.exists():
            raise CheckError("backend/requirements.txt not found")

    def check_frontend_dependencies(self):
        """Verify frontend node_modules are installed."""
        node_modules = Path('frontend/node_modules')
        if not node_modules.exists():
            raise CheckError(
                "Frontend dependencies not installed\n"
                "    Fix: cd frontend && npm install"
            )

    def check_docker_availability(self):
        """Verify Docker is installed and running."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise CheckError("Docker is installed but not responding")
        except FileNotFoundError:
            raise CheckError(
                "Docker not found\n"
                "    Fix: Install Docker Desktop: https://docker.com/get-started"
            )
        except subprocess.TimeoutExpired:
            raise CheckError("Docker command timed out")

        # Check if Docker daemon is running
        try:
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise CheckError(
                    "Docker daemon is not running\n"
                    "    Fix: Start Docker Desktop"
                )
        except subprocess.TimeoutExpired:
            raise CheckError("Docker daemon is not responding")

    def check_backend_port(self):
        """Check if backend port is available."""
        port = self.config.get('backend_port', DEFAULT_BACKEND_PORT)
        if not self._is_port_available(port):
            if self.kill_ports or self.auto_setup:
                print(f"{self._colorize(f'⚙️  Killing process on port {port}...', Color.YELLOW)}")
                if self._kill_port_process(port):
                    print(f"{self._colorize(f'✓ Port {port} freed', Color.GREEN)}")
                    return
                else:
                    raise CheckError(
                        f"Port {port} is already in use and could not be freed\n"
                        f"    Fix: Stop the existing process manually or use --port-backend <port>"
                    )
            else:
                raise CheckError(
                    f"Port {port} is already in use\n"
                    f"    Fix: Stop the existing process or use --port-backend <port>\n"
                    f"    Or use: python3 run.py --kill-ports"
                )

    def check_frontend_port(self):
        """Check if frontend port is available."""
        port = self.config.get('frontend_port', DEFAULT_FRONTEND_PORT)
        if not self._is_port_available(port):
            if self.kill_ports or self.auto_setup:
                print(f"{self._colorize(f'⚙️  Killing process on port {port}...', Color.YELLOW)}")
                if self._kill_port_process(port):
                    print(f"{self._colorize(f'✓ Port {port} freed', Color.GREEN)}")
                    return
                else:
                    raise CheckError(
                        f"Port {port} is already in use and could not be freed\n"
                        f"    Fix: Stop the existing process manually or use --port-frontend <port>"
                    )
            else:
                raise CheckError(
                    f"Port {port} is already in use\n"
                    f"    Fix: Stop the existing process or use --port-frontend <port>\n"
                    f"    Or use: python3 run.py --kill-ports"
                )

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open (service is listening)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _find_venv_python(self) -> Optional[Path]:
        """Find the Python executable in the backend virtual environment."""
        backend_dir = Path('backend')

        # Try Unix-style path
        venv_python = backend_dir / 'venv' / 'bin' / 'python'
        if venv_python.exists():
            return venv_python

        # Try Windows-style path
        venv_python = backend_dir / 'venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            return venv_python

        return None

    def _get_activate_command(self) -> str:
        """Get the virtual environment activation command for the current platform."""
        if self.platform_name == 'Windows':
            return 'venv\\Scripts\\activate'
        return 'source venv/bin/activate'

    def _get_postgres_start_command(self) -> str:
        """Get the PostgreSQL start command for the current platform."""
        if self.platform_name == 'Darwin':  # macOS
            return "Start PostgreSQL: brew services start postgresql@15"
        elif self.platform_name == 'Linux':
            return "Start PostgreSQL: sudo systemctl start postgresql"
        else:  # Windows
            return "Start PostgreSQL: Open Services panel and start postgresql service"

    def _get_redis_start_command(self) -> str:
        """Get the Redis start command for the current platform."""
        if self.platform_name == 'Darwin':  # macOS
            return "Start Redis: brew services start redis"
        elif self.platform_name == 'Linux':
            return "Start Redis: sudo systemctl start redis"
        else:  # Windows
            return "Start Redis: Download from https://redis.io/download or use Docker"

    def _start_postgres(self) -> bool:
        """Attempt to start PostgreSQL service."""
        try:
            if self.platform_name == 'Darwin':  # macOS
                result = subprocess.run(
                    ['brew', 'services', 'start', 'postgresql@15'],
                    capture_output=True,
                    timeout=30
                )
                if result.returncode != 0:
                    # Try generic postgresql
                    result = subprocess.run(
                        ['brew', 'services', 'start', 'postgresql'],
                        capture_output=True,
                        timeout=30
                    )
                # Wait for service to start
                time.sleep(3)
                return self._is_port_open('localhost', POSTGRES_PORT)
            elif self.platform_name == 'Linux':
                result = subprocess.run(
                    ['sudo', 'systemctl', 'start', 'postgresql'],
                    capture_output=True,
                    timeout=30
                )
                time.sleep(3)
                return result.returncode == 0 and self._is_port_open('localhost', POSTGRES_PORT)
            else:
                return False
        except Exception as e:
            print(f"{self._colorize(f'Warning: {e}', Color.YELLOW)}")
            return False

    def _start_redis(self) -> bool:
        """Attempt to start Redis service."""
        try:
            if self.platform_name == 'Darwin':  # macOS
                result = subprocess.run(
                    ['brew', 'services', 'start', 'redis'],
                    capture_output=True,
                    timeout=30
                )
                time.sleep(2)
                return self._is_port_open('localhost', REDIS_PORT)
            elif self.platform_name == 'Linux':
                result = subprocess.run(
                    ['sudo', 'systemctl', 'start', 'redis'],
                    capture_output=True,
                    timeout=30
                )
                time.sleep(2)
                return result.returncode == 0 and self._is_port_open('localhost', REDIS_PORT)
            else:
                return False
        except Exception as e:
            print(f"{self._colorize(f'Warning: {e}', Color.YELLOW)}")
            return False

    def _create_backend_venv(self) -> bool:
        """Create backend virtual environment and install dependencies."""
        try:
            backend_dir = Path('backend').resolve()

            # Create venv
            print(f"{self._colorize('  Creating virtual environment...', Color.GRAY)}")
            result = subprocess.run(
                [sys.executable, '-m', 'venv', 'venv'],
                cwd=str(backend_dir),
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f"{self._colorize(f'  Error: {result.stderr.decode()}', Color.RED)}")
                return False

            # Wait for venv to be fully created
            time.sleep(1)

            # Find pip in the new venv
            venv_pip = backend_dir / 'venv' / 'bin' / 'pip'
            if not venv_pip.exists():
                venv_pip = backend_dir / 'venv' / 'Scripts' / 'pip.exe'

            if not venv_pip.exists():
                print(f"{self._colorize(f'  Error: pip not found in venv', Color.RED)}")
                return False

            # Install dependencies
            print(f"{self._colorize('  Installing dependencies (this may take a few minutes)...', Color.GRAY)}")
            result = subprocess.run(
                [str(venv_pip), 'install', '-r', 'requirements.txt'],
                cwd=str(backend_dir),
                capture_output=False,  # Show output
                timeout=600  # 10 minutes
            )
            return result.returncode == 0
        except Exception as e:
            print(f"{self._colorize(f'Error creating venv: {e}', Color.YELLOW)}")
            import traceback
            traceback.print_exc()
            return False

    def _kill_port_process(self, port: int) -> bool:
        """Kill the process using the specified port."""
        try:
            if self.platform_name == 'Darwin' or self.platform_name == 'Linux':
                # Find process using lsof
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        subprocess.run(['kill', '-9', pid], timeout=5)
                    time.sleep(1)
                    return self._is_port_available(port)
            elif self.platform_name == 'Windows':
                # Find process using netstat
                result = subprocess.run(
                    ['netstat', '-ano', '|', 'findstr', f':{port}'],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Extract PID and kill
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) > 4:
                            pid = parts[-1]
                            subprocess.run(['taskkill', '/F', '/PID', pid], timeout=5)
                    time.sleep(1)
                    return self._is_port_available(port)
            return False
        except Exception as e:
            print(f"{self._colorize(f'Warning: {e}', Color.YELLOW)}")
            return False

    def print_results(self):
        """Print check results with colored output."""
        if self.errors:
            print(f"\n{self._colorize('❌ Prerequisite checks failed:', Color.RED + Color.BOLD)}\n")
            for name, error in self.errors:
                print(f"  {self._colorize('•', Color.RED)} {error}\n")
            print(f"{self._colorize('Fix the issues above and try again.', Color.RED)}\n")

        if self.warnings:
            print(f"\n{self._colorize('⚠️  Warnings:', Color.YELLOW + Color.BOLD)}\n")
            for name, warning in self.warnings:
                print(f"  {self._colorize('•', Color.YELLOW)} {warning}\n")

        if not self.errors and not self.warnings:
            print(f"{self._colorize('✅ All checks passed', Color.GREEN + Color.BOLD)}\n")
        elif not self.errors:
            print(f"{self._colorize('✅ All critical checks passed', Color.GREEN + Color.BOLD)}\n")

    def cleanup_started_services(self):
        """Stop any services that were auto-started."""
        if not self.services_started:
            return

        print(f"\n{self._colorize('Stopping auto-started services...', Color.YELLOW)}")

        for service in self.services_started:
            if service == 'postgresql':
                self._stop_postgres()
            elif service == 'redis':
                self._stop_redis()

    def _stop_postgres(self):
        """Stop PostgreSQL service."""
        try:
            if self.platform_name == 'Darwin':
                subprocess.run(
                    ['brew', 'services', 'stop', 'postgresql@15'],
                    capture_output=True,
                    timeout=10
                )
                print(f"{self._colorize('✓ PostgreSQL stopped', Color.GREEN)}")
            elif self.platform_name == 'Linux':
                subprocess.run(
                    ['sudo', 'systemctl', 'stop', 'postgresql'],
                    capture_output=True,
                    timeout=10
                )
                print(f"{self._colorize('✓ PostgreSQL stopped', Color.GREEN)}")
        except Exception as e:
            print(f"{self._colorize(f'Warning: Could not stop PostgreSQL: {e}', Color.YELLOW)}")

    def _stop_redis(self):
        """Stop Redis service."""
        try:
            if self.platform_name == 'Darwin':
                subprocess.run(
                    ['brew', 'services', 'stop', 'redis'],
                    capture_output=True,
                    timeout=10
                )
                print(f"{self._colorize('✓ Redis stopped', Color.GREEN)}")
            elif self.platform_name == 'Linux':
                subprocess.run(
                    ['sudo', 'systemctl', 'stop', 'redis'],
                    capture_output=True,
                    timeout=10
                )
                print(f"{self._colorize('✓ Redis stopped', Color.GREEN)}")
        except Exception as e:
            print(f"{self._colorize(f'Warning: Could not stop Redis: {e}', Color.YELLOW)}")


# ============================================================================
# LogMultiplexer
# ============================================================================

class LogMultiplexer:
    """Handles colored, prefixed output streaming from multiple processes."""

    def __init__(self, color_enabled: bool = True):
        self.color_enabled = color_enabled
        self.lock = asyncio.Lock()

        # Service-specific colors
        self.service_colors = {
            'system': Color.WHITE + Color.BOLD,
            'backend': Color.BLUE,
            'frontend': Color.MAGENTA,
            'docker': Color.CYAN,
        }

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    async def read_stream(self, stream: asyncio.StreamReader, service: str, stream_type: str):
        """Read from a stream line by line and print with service prefix."""
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break

                message = line.decode('utf-8', errors='replace').rstrip()
                if message:  # Skip empty lines
                    await self.log(service, message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.error('system', f"Error reading {service} {stream_type}: {e}")

    async def log(self, service: str, message: str, level: str = 'info'):
        """Print a log message with service prefix and color."""
        async with self.lock:
            color = self.service_colors.get(service, Color.WHITE)
            prefix = self._colorize(f"[{service}]", color)

            # Apply level-specific styling
            if level == 'error':
                message = self._colorize(message, Color.RED)
            elif level == 'warning':
                message = self._colorize(message, Color.YELLOW)
            elif level == 'success':
                message = self._colorize(message, Color.GREEN)

            print(f"{prefix} {message}", flush=True)

    async def info(self, service: str, message: str):
        """Print an info message."""
        await self.log(service, message, 'info')

    async def success(self, service: str, message: str):
        """Print a success message."""
        await self.log(service, message, 'success')

    async def warning(self, service: str, message: str):
        """Print a warning message."""
        await self.log(service, message, 'warning')

    async def error(self, service: str, message: str):
        """Print an error message."""
        await self.log(service, message, 'error')


# ============================================================================
# HealthMonitor
# ============================================================================

class HealthMonitor:
    """Monitors service health and readiness."""

    def __init__(self, logger: LogMultiplexer):
        self.logger = logger

    async def wait_for_service(self, name: str, url: str, timeout: int) -> bool:
        """
        Wait for a service to become healthy.
        Returns True if healthy, False if timeout.
        """
        await self.logger.info('system', f"Waiting for {name} to be ready...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.check_http_endpoint(url):
                await self.logger.success('system', f"{name} is ready")
                return True
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        await self.logger.error('system', f"{name} failed to start within {timeout}s")
        return False

    async def check_http_endpoint(self, url: str) -> bool:
        """Check if an HTTP endpoint is responding."""
        try:
            # Use urllib for simple sync HTTP check in async context
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_http_check, url)
            return True
        except Exception:
            return False

    def _sync_http_check(self, url: str):
        """Synchronous HTTP check helper."""
        if url.startswith("https://"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urlopen(url, timeout=2, context=ctx) as response:
                return response.status == 200
        else:
            with urlopen(url, timeout=2) as response:
                return response.status == 200


# ============================================================================
# ServiceManager
# ============================================================================

class ServiceManager:
    """Manages the lifecycle of all services."""

    def __init__(self, config: Dict[str, Any], logger: LogMultiplexer):
        self.config = config
        self.logger = logger
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.stream_tasks: List[asyncio.Task] = []
        self.health_monitor = HealthMonitor(logger)

    async def start_all(self):
        """Start all services based on configuration."""
        mode = self.config['mode']

        if mode == 'docker':
            await self.start_docker()
        else:
            if mode in ['dev', 'backend']:
                await self.start_backend()

            if mode in ['dev', 'frontend']:
                await self.start_frontend()

        # Wait for services to be healthy
        await self._wait_for_health()

    async def start_backend(self):
        """Start the FastAPI backend server."""
        venv_python = self._find_venv_python()
        if not venv_python:
            raise RuntimeError("Backend virtual environment not found")

        port = self.config.get('backend_port', DEFAULT_BACKEND_PORT)
        host = self.config.get('host', DEFAULT_HOST)

        cmd = [
            str(venv_python),
            '-m', 'uvicorn',
            'app.main:app',
            '--reload',
            '--port', str(port),
            '--host', host
        ]

        # Append SSL args when HTTPS is enabled
        if self.config.get('https'):
            ssl_cert = self.config.get('ssl_cert')
            ssl_key = self.config.get('ssl_key')
            if ssl_cert and ssl_key:
                cmd.extend(['--ssl-certfile', ssl_cert, '--ssl-keyfile', ssl_key])

        protocol = "https" if self.config.get('https') else "http"
        await self.logger.info('backend', f"Starting backend on {protocol}://{host}:{port}...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path('backend'))
        )

        self.processes['backend'] = process

        # Start log streaming tasks
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stdout, 'backend', 'stdout'))
        )
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stderr, 'backend', 'stderr'))
        )

    async def start_frontend(self):
        """Start the Vite frontend dev server."""
        port = self.config.get('frontend_port', DEFAULT_FRONTEND_PORT)
        host = self.config.get('host', DEFAULT_HOST)

        # Set environment variable for Vite port
        env = os.environ.copy()
        env['PORT'] = str(port)

        # Pass HTTPS configuration to Vite
        if self.config.get('https'):
            env['VITE_ENABLE_HTTPS'] = 'true'
            # VITE_API_URL is not set here — api.ts auto-detects using window.location.hostname

        cmd = ['npm', 'run', 'dev', '--', '--host', host]

        protocol = "https" if self.config.get('https') else "http"
        await self.logger.info('frontend', f"Starting frontend on {protocol}://{host}:{port}...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path('frontend')),
            env=env
        )

        self.processes['frontend'] = process

        # Start log streaming tasks
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stdout, 'frontend', 'stdout'))
        )
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stderr, 'frontend', 'stderr'))
        )

    async def start_docker(self):
        """Start Docker Compose stack."""
        cmd = [
            'docker', 'compose',
            '-f', 'docker/docker-compose.yml',
            'up'
        ]

        await self.logger.info('docker', "Starting Docker Compose stack...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        self.processes['docker'] = process

        # Start log streaming tasks
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stdout, 'docker', 'stdout'))
        )
        self.stream_tasks.append(
            asyncio.create_task(self.logger.read_stream(process.stderr, 'docker', 'stderr'))
        )

    async def _wait_for_health(self):
        """Wait for all services to become healthy."""
        mode = self.config['mode']
        protocol = "https" if self.config.get('https') else "http"

        if mode in ['dev', 'backend']:
            port = self.config.get('backend_port', DEFAULT_BACKEND_PORT)
            url = BACKEND_HEALTH_ENDPOINT.format(protocol=protocol, port=port)
            success = await self.health_monitor.wait_for_service(
                'Backend',
                url,
                BACKEND_STARTUP_TIMEOUT
            )
            if not success:
                raise RuntimeError("Backend failed to start")

        if mode in ['dev', 'frontend']:
            # For frontend, just wait a few seconds for Vite to start
            await asyncio.sleep(FRONTEND_STARTUP_TIMEOUT / 2)
            await self.logger.success('system', "Frontend is ready")

        if mode == 'docker':
            # Wait for docker services
            await asyncio.sleep(5)
            port = self.config.get('backend_port', DEFAULT_BACKEND_PORT)
            url = BACKEND_HEALTH_ENDPOINT.format(protocol="http", port=port)
            await self.health_monitor.wait_for_service(
                'Docker stack',
                url,
                BACKEND_STARTUP_TIMEOUT
            )

    async def stop_all(self):
        """Stop all running services gracefully."""
        if not self.processes:
            return

        await self.logger.info('system', "Shutting down...")

        # Cancel log streaming tasks
        for task in self.stream_tasks:
            task.cancel()

        # Try to wait for tasks to complete
        if self.stream_tasks:
            await asyncio.gather(*self.stream_tasks, return_exceptions=True)

        # Stop each process
        for service, process in self.processes.items():
            await self._stop_process(service, process)

        await self.logger.success('system', "Shutdown complete")

    async def _stop_process(self, service: str, process: asyncio.subprocess.Process):
        """Stop a single process gracefully."""
        if process.returncode is not None:
            # Already stopped
            return

        await self.logger.info(service, "Stopping...")

        try:
            # Send SIGTERM
            process.terminate()

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=SHUTDOWN_TIMEOUT)
                await self.logger.success(service, "Stopped")
            except asyncio.TimeoutError:
                # Force kill if timeout
                await self.logger.warning(service, "Force killing...")
                process.kill()
                await process.wait()
                await self.logger.success(service, "Killed")
        except ProcessLookupError:
            # Already dead
            pass

    def _find_venv_python(self) -> Optional[Path]:
        """Find the Python executable in the backend virtual environment."""
        # Use resolve() on the directory only to get an absolute path,
        # but NOT on the python symlink itself — resolving it would point
        # to the system Python and bypass venv site-packages detection.
        backend_dir = Path('backend').resolve()

        # Try Unix-style path
        venv_python = backend_dir / 'venv' / 'bin' / 'python'
        if venv_python.exists():
            return venv_python

        # Try Windows-style path
        venv_python = backend_dir / 'venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            return venv_python

        return None


# ============================================================================
# SignalHandler
# ============================================================================

class SignalHandler:
    """Handles graceful shutdown on SIGINT/SIGTERM."""

    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        self.shutdown_event = asyncio.Event()

    def setup(self):
        """Set up signal handlers."""
        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        self.shutdown_event.set()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()


# ============================================================================
# Utility Functions
# ============================================================================

def load_dotenv():
    """Load environment variables from .env file if it exists."""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())


def print_banner(config: Dict[str, Any], color_enabled: bool = True):
    """Print startup banner."""
    def colorize(text: str, color: str) -> str:
        if not color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    mode_str = config['mode'].upper()
    print(f"\n{colorize('=' * 60, Color.CYAN)}")
    print(f"{colorize('  DysLex AI - Starting in ' + mode_str + ' mode', Color.CYAN + Color.BOLD)}")
    print(f"{colorize('=' * 60, Color.CYAN)}\n")


def _get_local_ip() -> Optional[str]:
    """Get the machine's local network IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return None


def print_ready_banner(config: Dict[str, Any], color_enabled: bool = True):
    """Print ready banner with service URLs."""
    def colorize(text: str, color: str) -> str:
        if not color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    mode = config['mode']
    host = config.get('host', DEFAULT_HOST)
    backend_port = config.get('backend_port', DEFAULT_BACKEND_PORT)
    frontend_port = config.get('frontend_port', DEFAULT_FRONTEND_PORT)
    network = host == '0.0.0.0'
    local_ip = _get_local_ip() if network else None
    protocol = "https" if config.get('https') else "http"

    print(f"\n{colorize('=' * 60, Color.GREEN)}")
    print(f"{colorize('  🚀 DysLex AI is ready!', Color.GREEN + Color.BOLD)}")
    print(f"{colorize('=' * 60, Color.GREEN)}")

    if mode in ['dev', 'frontend']:
        print(f"  {colorize('Frontend:', Color.BOLD)} {protocol}://localhost:{frontend_port}")
        if network and local_ip:
            print(f"  {colorize('Frontend (network):', Color.BOLD)} {protocol}://{local_ip}:{frontend_port}")

    if mode in ['dev', 'backend']:
        print(f"  {colorize('Backend API:', Color.BOLD)} {protocol}://localhost:{backend_port}")
        print(f"  {colorize('API Docs:', Color.BOLD)} {protocol}://localhost:{backend_port}/docs")
        if network and local_ip:
            print(f"  {colorize('Backend API (network):', Color.BOLD)} {protocol}://{local_ip}:{backend_port}")

    if mode == 'docker':
        print(f"  {colorize('Frontend:', Color.BOLD)} http://localhost:{frontend_port}")
        print(f"  {colorize('Backend API:', Color.BOLD)} http://localhost:{backend_port}")
        print(f"  {colorize('API Docs:', Color.BOLD)} http://localhost:{backend_port}/docs")

    print(f"\n  {colorize('Press Ctrl+C to stop', Color.GRAY)}")
    print(f"{colorize('=' * 60, Color.GREEN)}\n")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='DysLex AI - Unified Development Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                    # Start backend + frontend (localhost only)
  python run.py --host 0.0.0.0     # Start on all interfaces (network accessible)
  python run.py --docker           # Start with Docker Compose
  python run.py --backend-only     # Start only backend
  python run.py --frontend-only    # Start only frontend
  python run.py --check-only       # Run checks without starting

For more information, see: https://github.com/anthropics/dyslex-ai
        """
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--docker',
        action='store_true',
        help='Run in Docker Compose mode'
    )
    mode_group.add_argument(
        '--backend-only',
        action='store_true',
        help='Run only the backend API server'
    )
    mode_group.add_argument(
        '--frontend-only',
        action='store_true',
        help='Run only the frontend dev server'
    )

    # Options
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip prerequisite checks (use with caution)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default=DEFAULT_HOST,
        choices=['localhost', '0.0.0.0'],
        help=f'Host to bind services to (default: {DEFAULT_HOST}). Use 0.0.0.0 for network access'
    )
    parser.add_argument(
        '--port-backend',
        type=int,
        default=DEFAULT_BACKEND_PORT,
        help=f'Backend port (default: {DEFAULT_BACKEND_PORT})'
    )
    parser.add_argument(
        '--port-frontend',
        type=int,
        default=DEFAULT_FRONTEND_PORT,
        help=f'Frontend port (default: {DEFAULT_FRONTEND_PORT})'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Run prerequisite checks only, do not start services'
    )
    parser.add_argument(
        '--auto-setup',
        action='store_true',
        help='Automatically start services (PostgreSQL, Redis) and create venv if needed'
    )
    parser.add_argument(
        '--kill-ports',
        action='store_true',
        help='Automatically kill processes using required ports'
    )

    # HTTPS / SSL (enabled by default)
    parser.add_argument(
        '--https',
        action='store_true',
        default=True,
        help='Enable HTTPS (default: enabled)'
    )
    parser.add_argument(
        '--no-https',
        action='store_false',
        dest='https',
        help='Disable HTTPS and use plain HTTP'
    )
    parser.add_argument(
        '--ssl-cert',
        type=str,
        default=None,
        help='Path to SSL certificate file (default: certs/dev/localhost+2.pem)'
    )
    parser.add_argument(
        '--ssl-key',
        type=str,
        default=None,
        help='Path to SSL private key file (default: certs/dev/localhost+2-key.pem)'
    )

    return parser


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point."""
    # Ensure we're in the project root directory
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # Load environment variables from .env if present
    load_dotenv()

    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Determine mode
    if args.docker:
        mode = 'docker'
    elif args.backend_only:
        mode = 'backend'
    elif args.frontend_only:
        mode = 'frontend'
    else:
        mode = 'dev'

    # Resolve SSL certificate paths
    ssl_cert = args.ssl_cert
    ssl_key = args.ssl_key
    if args.https and not ssl_cert:
        ssl_cert = str(Path('certs/dev/localhost+2.pem').resolve())
    if args.https and not ssl_key:
        ssl_key = str(Path('certs/dev/localhost+2-key.pem').resolve())

    if args.https:
        if not Path(ssl_cert).exists() or not Path(ssl_key).exists():
            print(f"\n{Color.YELLOW}SSL certificates not found — falling back to HTTP.{Color.RESET}")
            print(f"  To enable HTTPS, run: bash scripts/generate-dev-certs.sh\n")
            args.https = False
            ssl_cert = None
            ssl_key = None

    # Build configuration
    config = {
        'mode': mode,
        'host': args.host,
        'backend_port': args.port_backend,
        'frontend_port': args.port_frontend,
        'verbose': args.verbose,
        'color_enabled': not args.no_color and sys.stdout.isatty(),
        'auto_setup': args.auto_setup,
        'kill_ports': args.kill_ports,
        'https': args.https,
        'ssl_cert': ssl_cert,
        'ssl_key': ssl_key,
    }

    # Print banner
    if not args.check_only:
        print_banner(config, config['color_enabled'])

    # Run prerequisite checks
    checker = None
    if not args.skip_checks:
        checker = PrerequisiteChecker(mode, config, config['color_enabled'])
        checks_passed = checker.check_all()
        checker.print_results()

        if not checks_passed:
            sys.exit(1)

        if args.check_only:
            sys.exit(0)

    # Initialize logger
    logger = LogMultiplexer(config['color_enabled'])

    # Initialize service manager
    service_manager = ServiceManager(config, logger)

    # Set up signal handler
    signal_handler = SignalHandler(service_manager)
    signal_handler.setup()

    try:
        # Start services
        await service_manager.start_all()

        # Print ready banner
        print_ready_banner(config, config['color_enabled'])

        # Wait for shutdown signal
        await signal_handler.wait_for_shutdown()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        await logger.error('system', f"Fatal error: {e}")
        if config['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up
        await service_manager.stop_all()

        # Stop any auto-started services
        if checker and config.get('auto_setup'):
            checker.cleanup_started_services()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        sys.exit(0)
