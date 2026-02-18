#!/usr/bin/env python3
"""
DysLex AI - Unified Development Launcher

A comprehensive script to start, monitor, and stop all DysLex AI services with a single command.
Supports development mode, Docker mode, and individual service modes with intelligent prerequisite
checking, colored log output, health monitoring, and graceful shutdown.

Usage:
    python run.py                    # Development mode (backend + frontend)
    python run.py --auto-setup       # Install prerequisites + start everything
    python run.py --auto-setup -y    # Same, skip confirmation prompts
    python run.py --host 0.0.0.0     # Network accessible (other devices can connect)
    python run.py --docker           # Docker Compose mode
    python run.py --backend-only     # Backend only
    python run.py --frontend-only    # Frontend only
    python run.py --check-only       # Run checks without starting services

Requirements (auto-installed with --auto-setup):
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

Why sudo? (Linux only):
    When using --auto-setup on Linux, this script may prompt for your sudo password.
    It is used for two things:
      1. Installing system packages via your package manager (apt-get, dnf, pacman, or snap)
      2. Starting system services (PostgreSQL and Redis via systemctl)
    On macOS, Homebrew handles packages without sudo. On Windows, Chocolatey is used instead.
    Without --auto-setup, sudo is never invoked.
    If running as root (e.g., in Docker containers), sudo is skipped automatically.

License:
    Apache 2.0 - See LICENSE file
"""

import asyncio
import argparse
import atexit
from enum import Enum
import json
import shutil
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
from urllib.error import HTTPError, URLError


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

BACKEND_HEALTH_ENDPOINT = "{protocol}://localhost:{port}/health/ready"  # Validates DB + Redis, not just process liveness
BACKEND_STARTUP_TIMEOUT = 30  # seconds (overridable via DYSLEX_BACKEND_TIMEOUT env var or --startup-timeout)
FRONTEND_STARTUP_TIMEOUT = 10  # seconds (overridable via DYSLEX_FRONTEND_TIMEOUT env var)
HEALTH_CHECK_INTERVAL = 1  # seconds
HEALTH_CHECK_REQUEST_TIMEOUT = 5  # seconds per HTTP request (cold starts with SQLAlchemy lazy init take longer)

SHUTDOWN_TIMEOUT = 5  # seconds to wait for graceful shutdown

# Root detection — when running as root (e.g., in Docker containers),
# sudo is unnecessary and may not even be installed.
IS_ROOT = (os.getuid() == 0) if hasattr(os, 'getuid') else False


def _sudo() -> List[str]:
    """Return ['sudo'] prefix, or [] if already running as root."""
    return [] if IS_ROOT else ['sudo']


def _sudo_user(user: str) -> List[str]:
    """Return command prefix to run as a different user.

    When root: ['runuser', '-u', user, '--']
    When not root: ['sudo', '-u', user]
    """
    if IS_ROOT:
        return ['runuser', '-u', user, '--']
    return ['sudo', '-u', user]


def _shell_sudo() -> str:
    """Return 'sudo ' or '' for use inside shell command strings."""
    return '' if IS_ROOT else 'sudo '


def _shell_sudo_E() -> str:
    """Return 'sudo -E ' or '' for use inside shell command strings."""
    return '' if IS_ROOT else 'sudo -E '

# NVIDIA NIM defaults (must match backend/app/config.py)
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_MODELS = [
    ("nvidia/nemotron-3-nano-30b-a3b", "LLM (corrections, brainstorm, mind map)"),
    ("nvidia/llama-3.1-nemotron-nano-vl-8b-v1", "Vision (image analysis)"),
]
NVIDIA_NIM_PING_TIMEOUT = 15  # seconds per model

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
# Dependency Pre-Scan Types
# ============================================================================

class DepState(Enum):
    """State of a dependency detected during pre-scan."""
    INSTALLED = 'installed'
    MISSING = 'MISSING'
    OUTDATED = 'OUTDATED'
    RUNNING = 'running'
    STOPPED = 'stopped'


class DependencyStatus:
    """Result of scanning a single dependency."""

    __slots__ = ('name', 'state', 'version', 'action', 'critical')

    def __init__(
        self,
        name: str,
        state: DepState,
        version: str = '-',
        action: str = '',
        critical: bool = True,
    ):
        self.name = name
        self.state = state
        self.version = version
        self.action = action
        self.critical = critical


# ============================================================================
# ProcessLock — Prevent Concurrent Instances
# ============================================================================

class ProcessLock:
    """File-based lock to prevent multiple run.py instances from running simultaneously.

    Uses fcntl.flock() on Unix and msvcrt.locking() on Windows.
    The lock file stores the owning PID for diagnostics.
    """

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        """Try to acquire the lock (non-blocking). Returns True on success.

        If the lock is held by a dead process (stale lock), automatically
        cleans up and retries once.
        """
        return self._try_acquire(allow_stale_recovery=True)

    def _try_acquire(self, allow_stale_recovery: bool = False) -> bool:
        """Internal lock acquisition with optional stale lock recovery."""
        try:
            self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR)
            if platform.system() == 'Windows':
                import msvcrt
                try:
                    msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
                except OSError:
                    if allow_stale_recovery and self._recover_stale_lock():
                        return self._try_acquire(allow_stale_recovery=False)
                    self._read_owner_pid()
                    os.close(self._fd)
                    self._fd = None
                    return False
            else:
                import fcntl
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    if allow_stale_recovery and self._recover_stale_lock():
                        return self._try_acquire(allow_stale_recovery=False)
                    self._read_owner_pid()
                    os.close(self._fd)
                    self._fd = None
                    return False

            # Write our PID
            os.ftruncate(self._fd, 0)
            os.lseek(self._fd, 0, os.SEEK_SET)
            os.write(self._fd, str(os.getpid()).encode())
            return True
        except Exception:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            return False

    def _recover_stale_lock(self) -> bool:
        """Check if the lock holder is dead. If so, remove the stale lock and return True."""
        try:
            if self._fd is None:
                return False
            os.lseek(self._fd, 0, os.SEEK_SET)
            data = os.read(self._fd, 32)
            pid_str = data.decode().strip()
            if not pid_str:
                return False
            pid = int(pid_str)
            # Check if process is alive
            os.kill(pid, 0)
            # Process is alive — lock is valid, not stale
            return False
        except PermissionError:
            # PID exists but owned by another user — lock is valid
            return False
        except ProcessLookupError:
            # PID doesn't exist — stale lock, proceed to cleanup
            pass
        except (ValueError, OSError):
            # Can't parse PID or read file — try recovery anyway
            pass

        # Close the fd and remove the stale lock file
        try:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
        except Exception:
            pass
        try:
            self.lock_path.unlink(missing_ok=True)
            print(f"{Color.YELLOW}Removed stale lock file (previous process is no longer running).{Color.RESET}")
            return True
        except Exception:
            return False

    def _read_owner_pid(self):
        """Read and print the PID of the process holding the lock."""
        try:
            if self._fd is not None:
                os.lseek(self._fd, 0, os.SEEK_SET)
                data = os.read(self._fd, 32)
                pid = data.decode().strip()
                if pid:
                    print(f"{Color.RED}Another instance of run.py is already running (PID {pid}).{Color.RESET}")
                    print(f"  If this is stale, delete {self.lock_path} and retry.")
                    return
        except Exception:
            pass
        print(f"{Color.RED}Another instance of run.py is already running.{Color.RESET}")
        print(f"  If this is stale, delete {self.lock_path} and retry.")

    def release(self):
        """Release the lock and remove the lock file."""
        if self._fd is not None:
            try:
                if platform.system() == 'Windows':
                    import msvcrt
                    try:
                        msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
                    except OSError:
                        pass
                else:
                    import fcntl
                    try:
                        fcntl.flock(self._fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(self._fd)
                self._fd = None
            except Exception:
                pass
            try:
                self.lock_path.unlink(missing_ok=True)
            except Exception:
                pass


# ============================================================================
# SetupState — Checkpoint / Resume for Auto-Setup
# ============================================================================

class SetupState:
    """Tracks auto-setup progress in a JSON checkpoint file.

    Allows resuming from the exact point of interruption after Ctrl+C or failure.
    The state file is deleted on full success so the next run starts clean.
    """

    STEPS = [
        'system_prerequisites',
        'node_install',
        'postgres_install',
        'redis_install',
        'venv_create',
        'pip_light_packages',
        'pip_heavy_packages',
        'npm_install',
        'env_file',
    ]

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load state from disk, or return empty state."""
        try:
            if self.state_path.exists():
                return json.loads(self.state_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
        return {"completed_steps": []}

    def _save(self):
        """Atomically persist state to disk."""
        atomic_write(self.state_path, json.dumps(self._state, indent=2) + '\n')

    def is_step_done(self, step: str) -> bool:
        """Check if a step has already been completed."""
        return step in self._state.get("completed_steps", [])

    def mark_done(self, step: str):
        """Mark a step as completed and persist."""
        completed = self._state.setdefault("completed_steps", [])
        if step not in completed:
            completed.append(step)
        self._save()

    def clear(self):
        """Remove the state file (called on full success or rollback)."""
        try:
            self.state_path.unlink(missing_ok=True)
        except OSError:
            pass

    def has_any_progress(self) -> bool:
        """True if any steps were previously completed."""
        return len(self._state.get("completed_steps", [])) > 0

    def increment_attempt(self, step: str) -> int:
        """Increment and return the attempt count for a step."""
        counts = self._state.setdefault("attempt_counts", {})
        counts[step] = counts.get(step, 0) + 1
        self._save()
        return counts[step]

    def get_attempts(self, step: str) -> int:
        """Return the current attempt count for a step."""
        return self._state.get("attempt_counts", {}).get(step, 0)


# ============================================================================
# Utility: Atomic File Write
# ============================================================================

def atomic_write(target: Path, content: str):
    """Write content to a file atomically via a temp file + rename.

    On POSIX, Path.replace() is atomic within the same filesystem.
    This prevents partial writes if the process is interrupted.
    """
    tmp_path = target.with_suffix(target.suffix + '.tmp')
    tmp_path.write_text(content)
    tmp_path.replace(target)


# ============================================================================
# Utility: Smart First-Run Detection
# ============================================================================

def should_auto_setup(script_dir: Path) -> Tuple[bool, str]:
    """Determine whether auto-setup should be triggered.

    Returns (should_trigger, reason) tuple.
    Checks:
    1. Venv existence (both 'venv' and '.venv' naming conventions)
    2. Venv integrity (python binary exists AND core imports work)
    3. node_modules existence and completeness (package-lock.json marker)
    4. .env file existence
    """
    backend_dir = script_dir / 'backend'
    frontend_dir = script_dir / 'frontend'

    # Check for venv in both naming conventions
    venv_dir = None
    for name in ('venv', '.venv'):
        candidate = backend_dir / name
        if candidate.is_dir():
            venv_dir = candidate
            break

    venv_ok = False
    if venv_dir:
        # Validate venv integrity: python binary must exist
        python_bin = venv_dir / 'bin' / 'python'
        if not python_bin.exists():
            python_bin = venv_dir / 'Scripts' / 'python.exe'

        if python_bin.exists():
            # Validate core imports work (catches partial installs)
            try:
                result = subprocess.run(
                    [str(python_bin), '-c', 'import fastapi; import sqlalchemy'],
                    capture_output=True, timeout=10,
                )
                venv_ok = result.returncode == 0
            except Exception:
                venv_ok = False

        if not venv_ok:
            return (True, "Backend venv exists but core dependencies are missing or broken")

    # Check node_modules
    node_modules = frontend_dir / 'node_modules'
    node_modules_ok = node_modules.is_dir() and (node_modules / '.package-lock.json').exists()

    # Check .env
    env_ok = (script_dir / '.env').is_file() or (backend_dir / '.env').is_file()

    # If nothing exists at all, it's a first run
    if not venv_dir and not node_modules.is_dir() and not env_ok:
        return (True, "First run detected — no backend venv, node_modules, or .env found")

    # If venv is missing entirely
    if not venv_dir:
        return (True, "Backend virtual environment not found")

    # If node_modules is missing or incomplete
    if not node_modules_ok:
        return (True, "Frontend dependencies are missing or incomplete")

    # Everything looks fine
    return (False, "")


# ============================================================================
# Port utilities
# ============================================================================

def _find_pids_on_port(port: int) -> list:
    """Find PIDs using a port. Tries lsof first, falls back to /proc/net/tcp."""
    # Try lsof first
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')
    except FileNotFoundError:
        pass

    # Fallback: parse /proc/net/tcp and /proc/net/tcp6 (Linux)
    try:
        hex_port = f'{port:04X}'
        inodes = set()
        for tcp_file in ('/proc/net/tcp', '/proc/net/tcp6'):
            try:
                with open(tcp_file, 'r') as f:
                    for line in f.readlines()[1:]:  # skip header
                        fields = line.split()
                        if len(fields) >= 10:
                            local_port = fields[1].split(':')[1]
                            if local_port == hex_port:
                                inodes.add(fields[9])
            except FileNotFoundError:
                continue
        if not inodes:
            return []
        # Find PIDs owning those socket inodes
        pids = []
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            fd_dir = f'/proc/{pid_dir}/fd'
            try:
                for fd in os.listdir(fd_dir):
                    try:
                        link = os.readlink(f'{fd_dir}/{fd}')
                        if link.startswith('socket:['):
                            inode = link[8:-1]
                            if inode in inodes:
                                pids.append(pid_dir)
                                break
                    except (OSError, ValueError):
                        continue
            except (PermissionError, FileNotFoundError):
                continue
        return pids
    except Exception:
        return []


# ============================================================================
# PackageInstaller
# ============================================================================

class PackageInstaller:
    """Platform-aware package installer for auto-setup mode.

    Ports installation logic from scripts/setup-mac.sh, scripts/setup-linux.sh,
    and scripts/setup-windows.ps1 into Python so that `run.py --auto-setup`
    can install missing prerequisites automatically.
    """

    def __init__(self, color_enabled: bool = True, yes: bool = False):
        self.color_enabled = color_enabled
        self.yes = yes  # Skip confirmation prompts
        self.platform_name = platform.system()
        self._pkg_manager: Optional[str] = None
        self._linux_distro: Optional[str] = None
        self._dpkg_broken: bool = False

    def _colorize(self, text: str, color: str) -> str:
        if not self.color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    # ------------------------------------------------------------------
    # Retry logic for network operations
    # ------------------------------------------------------------------

    def _retry_command(
        self,
        cmd: List[str],
        description: str,
        max_retries: int = 3,
        timeout: int = 600,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Run a command with retry and exponential backoff for network operations.

        Retries on non-zero exit code. Does NOT retry on KeyboardInterrupt or timeout.
        """
        last_result = None
        for attempt in range(1, max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=False,
                    text=True,
                    timeout=timeout,
                    cwd=cwd,
                )
                if result.returncode == 0:
                    return result
                last_result = result
                if attempt < max_retries:
                    delay = 2 ** attempt  # 2s, 4s, 8s
                    print(self._colorize(
                        f'  Attempt {attempt}/{max_retries} failed ({description}). '
                        f'Retrying in {delay}s...',
                        Color.YELLOW,
                    ))
                    time.sleep(delay)
            except subprocess.TimeoutExpired:
                raise
            except KeyboardInterrupt:
                raise
        return last_result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # User confirmation
    # ------------------------------------------------------------------

    def _confirm(self, prompt: str) -> bool:
        """Ask user for confirmation. Returns True if --yes or user accepts.

        In non-interactive environments (no TTY on stdin), auto-confirms
        to prevent hanging in CI/Docker/piped input scenarios.
        """
        if self.yes:
            print(f"{self._colorize(prompt + ' (auto-confirmed with --yes)', Color.GRAY)}")
            return True
        if not sys.stdin.isatty():
            print(f"{self._colorize(prompt + ' (auto-confirmed: non-interactive mode)', Color.GRAY)}")
            return True
        try:
            answer = input(f"{prompt} [Y/n] ").strip().lower()
            return answer in ('', 'y', 'yes')
        except (EOFError, KeyboardInterrupt):
            return False

    # ------------------------------------------------------------------
    # Platform detection
    # ------------------------------------------------------------------

    def _detect_package_manager(self) -> Optional[str]:
        """Detect the system package manager."""
        if self._pkg_manager is not None:
            return self._pkg_manager

        if self.platform_name == 'Darwin':
            self._pkg_manager = 'brew'
        elif self.platform_name == 'Windows':
            self._pkg_manager = 'choco'
        elif self.platform_name == 'Linux':
            distro = self._detect_linux_distro()
            manager_map = {
                'debian': 'apt',
                'fedora': 'dnf',
                'arch': 'pacman',
            }
            self._pkg_manager = manager_map.get(distro) if distro else None
        return self._pkg_manager

    def _detect_linux_distro(self) -> Optional[str]:
        """Parse /etc/os-release to determine Linux distro family."""
        if self._linux_distro is not None:
            return self._linux_distro

        os_release = Path('/etc/os-release')
        if not os_release.exists():
            return None

        info: Dict[str, str] = {}
        with open(os_release) as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key] = value.strip('"')

        distro_id = info.get('ID', '').lower()
        id_like = info.get('ID_LIKE', '').lower()

        debian_ids = {'ubuntu', 'debian', 'pop', 'linuxmint', 'elementary', 'zorin'}
        fedora_ids = {'fedora', 'rhel', 'centos', 'rocky', 'alma'}
        arch_ids = {'arch', 'manjaro', 'endeavouros'}

        if distro_id in debian_ids:
            self._linux_distro = 'debian'
        elif distro_id in fedora_ids:
            self._linux_distro = 'fedora'
        elif distro_id in arch_ids:
            self._linux_distro = 'arch'
        elif any(d in id_like for d in ('debian', 'ubuntu')):
            self._linux_distro = 'debian'
        elif any(d in id_like for d in ('fedora', 'rhel')):
            self._linux_distro = 'fedora'
        elif 'arch' in id_like:
            self._linux_distro = 'arch'

        return self._linux_distro

    # ------------------------------------------------------------------
    # Command helpers
    # ------------------------------------------------------------------

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 300,
        capture: bool = False,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Run a command with timeout and error handling."""
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

    def _is_command_available(self, cmd: str) -> bool:
        """Check if a command is available on PATH."""
        try:
            result = subprocess.run(
                ['which', cmd] if self.platform_name != 'Windows' else ['where', cmd],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Alternative install sources (fallbacks)
    # ------------------------------------------------------------------

    def _has_winget(self) -> bool:
        """Check if winget is available (Windows 10 1709+ / Windows 11)."""
        return self.platform_name == 'Windows' and self._is_command_available('winget')

    def _has_snap(self) -> bool:
        """Check if snap is available (Ubuntu, many Linux distros)."""
        return self.platform_name == 'Linux' and self._is_command_available('snap')

    def _has_docker(self) -> bool:
        """Check if Docker is available for container-based fallbacks."""
        try:
            result = subprocess.run(['docker', 'info'], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def _install_via_winget(self, package_id: str) -> bool:
        """Install a package via winget (Windows fallback). Returns True on success."""
        if not self._has_winget():
            return False
        print(self._colorize(f'  Trying winget: {package_id}...', Color.GRAY))
        try:
            result = subprocess.run(
                ['winget', 'install', '--id', package_id, '-e',
                 '--accept-source-agreements', '--accept-package-agreements'],
                timeout=600,
            )
            if result.returncode == 0:
                self._refresh_windows_path()
            return result.returncode == 0
        except Exception:
            return False

    def _install_node_via_fnm(self) -> bool:
        """Install Node.js via fnm (Fast Node Manager) — works on all platforms.
        fnm is a single binary with no dependencies.
        """
        print(self._colorize('  Trying fnm (Fast Node Manager)...', Color.GRAY))
        try:
            # Install fnm itself
            if not self._is_command_available('fnm'):
                if self.platform_name == 'Windows':
                    result = subprocess.run(
                        ['powershell', '-NoProfile', '-Command',
                         'irm https://fnm.vercel.app/install | iex'],
                        capture_output=True, timeout=120,
                    )
                    self._refresh_windows_path()
                else:
                    result = subprocess.run(
                        ['bash', '-c', 'curl -fsSL https://fnm.vercel.app/install | bash'],
                        capture_output=True, timeout=120,
                    )
                    # Add fnm to PATH for current session
                    fnm_dir = Path.home() / '.local' / 'share' / 'fnm'
                    if fnm_dir.exists():
                        os.environ['PATH'] = str(fnm_dir) + ':' + os.environ.get('PATH', '')
                    fnm_dir2 = Path.home() / '.fnm'
                    if fnm_dir2.exists():
                        os.environ['PATH'] = str(fnm_dir2) + ':' + os.environ.get('PATH', '')

            if not self._is_command_available('fnm'):
                return False

            # Install Node.js 20 via fnm
            subprocess.run(['fnm', 'install', '20'], timeout=120)
            subprocess.run(['fnm', 'use', '20'], capture_output=True, timeout=10)
            subprocess.run(['fnm', 'default', '20'], capture_output=True, timeout=10)

            # fnm needs eval in shell — set PATH manually for this session
            fnm_dir = subprocess.run(
                ['fnm', 'env', '--shell', 'bash'],
                capture_output=True, text=True, timeout=10,
            )
            if fnm_dir.returncode == 0:
                for line in fnm_dir.stdout.strip().split('\n'):
                    if 'PATH=' in line or 'FNM_' in line:
                        line = line.replace('export ', '').strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip('"').strip("'")
                            value = value.replace('${PATH}', os.environ.get('PATH', ''))
                            value = value.replace('$PATH', os.environ.get('PATH', ''))
                            os.environ[key] = value

            return self._is_command_available('node')
        except Exception:
            return False

    def _install_via_snap(self, snap_name: str, classic: bool = False) -> bool:
        """Install a package via snap (Linux fallback). Returns True on success."""
        if not self._has_snap():
            return False
        print(self._colorize(f'  Trying snap: {snap_name}...', Color.GRAY))
        try:
            cmd = [*_sudo(), 'snap', 'install', snap_name]
            if classic:
                cmd.append('--classic')
            result = subprocess.run(cmd, timeout=300)
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Homebrew (macOS)
    # ------------------------------------------------------------------

    def _ensure_homebrew(self) -> bool:
        """Install Homebrew on macOS if missing. Returns True on success."""
        if self._is_command_available('brew'):
            return True

        print(self._colorize('⚙️  Homebrew not found. It is required to install packages on macOS.', Color.YELLOW))
        if not self._confirm('Install Homebrew?'):
            return False

        print(self._colorize('  Installing Homebrew...', Color.GRAY))
        try:
            result = subprocess.run(
                ['/bin/bash', '-c',
                 'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'],
                timeout=600,
            )
            if result.returncode != 0:
                return False

            # Add brew to PATH for Apple Silicon
            brew_path = Path('/opt/homebrew/bin/brew')
            if brew_path.exists():
                result = subprocess.run(
                    [str(brew_path), 'shellenv'],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith('export '):
                            parts = line.replace('export ', '').split('=', 1)
                            if len(parts) == 2:
                                key = parts[0]
                                value = parts[1].strip('"').strip("'")
                                # Expand $PATH references
                                value = value.replace('${PATH}', os.environ.get('PATH', ''))
                                value = value.replace('$PATH', os.environ.get('PATH', ''))
                                os.environ[key] = value

            print(self._colorize('✓ Homebrew installed', Color.GREEN))
            return True
        except Exception as e:
            print(self._colorize(f'  Error installing Homebrew: {e}', Color.RED))
            return False

    # ------------------------------------------------------------------
    # Chocolatey (Windows)
    # ------------------------------------------------------------------

    def _ensure_chocolatey(self) -> bool:
        """Install Chocolatey on Windows if missing. Returns True on success."""
        if self._is_command_available('choco'):
            return True

        print(self._colorize('⚙️  Chocolatey not found. It is required to install packages on Windows.', Color.YELLOW))
        if not self._confirm('Install Chocolatey?'):
            return False

        print(self._colorize('  Installing Chocolatey...', Color.GRAY))
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                 "[System.Net.ServicePointManager]::SecurityProtocol = "
                 "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                 "iex ((New-Object System.Net.WebClient).DownloadString("
                 "'https://community.chocolatey.org/install.ps1'))"],
                timeout=300,
            )
            if result.returncode == 0:
                # Refresh PATH
                self._refresh_windows_path()
                print(self._colorize('✓ Chocolatey installed', Color.GREEN))
                return True
            return False
        except Exception as e:
            print(self._colorize(f'  Error installing Chocolatey: {e}', Color.RED))
            return False

    def _refresh_windows_path(self):
        """Refresh PATH on Windows after package installations."""
        if self.platform_name != 'Windows':
            return
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '[System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + '
                 '[System.Environment]::GetEnvironmentVariable("Path","User")'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                os.environ['PATH'] = result.stdout.strip()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # dpkg recovery (Debian/Ubuntu)
    # ------------------------------------------------------------------

    def _fix_dpkg(self) -> bool:
        """Run 'dpkg --configure -a' if dpkg is in a broken state.

        Returns True if dpkg is healthy, False if broken and unfixable.
        This can happen when a previous apt operation was interrupted
        (e.g., in Docker builds, OOM kills, or Ctrl+C during install).
        """
        if self._detect_package_manager() != 'apt':
            return True
        # Quick check: run a harmless dpkg command to see if it complains
        result = subprocess.run(
            [*_sudo(), 'dpkg', '--audit'],
            capture_output=True, text=True, timeout=30,
        )
        # Also try apt-get check which surfaces the "dpkg was interrupted" error
        result2 = subprocess.run(
            [*_sudo(), 'apt-get', 'check'],
            capture_output=True, text=True, timeout=30,
        )
        stderr_combined = (result.stderr or '') + (result2.stderr or '')
        if 'dpkg --configure -a' not in stderr_combined and result2.returncode == 0:
            return True  # dpkg is fine

        print(self._colorize('⚙️  Fixing interrupted dpkg state...', Color.YELLOW))
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.run(
            [*_sudo(), 'dpkg', '--configure', '-a'],
            timeout=300,
            env=env,
        )
        # Verify the fix actually worked
        verify = subprocess.run(
            [*_sudo(), 'apt-get', 'check'],
            capture_output=True, text=True, timeout=30,
        )
        if verify.returncode == 0:
            print(self._colorize('✓ dpkg state recovered', Color.GREEN))
            return True
        else:
            print(self._colorize('✗ Could not fix dpkg automatically.', Color.RED))
            print(self._colorize('  Run manually: sudo dpkg --configure -a', Color.YELLOW))
            self._dpkg_broken = True
            return False

    # ------------------------------------------------------------------
    # Python 3.11+
    # ------------------------------------------------------------------

    def install_python(self) -> Optional[str]:
        """Install Python 3.11+ via platform package manager.

        Returns the absolute path to the new python3.11 binary on success,
        or None on failure. The caller can use os.execv() to re-exec the
        script under the new interpreter in the same terminal session.
        """
        print(self._colorize('⚙️  Python 3.11+ not found.', Color.YELLOW))
        if not self._confirm('Install Python 3.11?'):
            return None

        pkg = self._detect_package_manager()
        if not pkg:
            print(self._colorize('  Could not detect package manager', Color.RED))
            return None

        print(self._colorize('  Installing Python 3.11...', Color.GRAY))
        try:
            if pkg == 'brew':
                if not self._ensure_homebrew():
                    return None
                self._run_command(['brew', 'install', 'python@3.11'], timeout=600)

            elif pkg == 'apt':
                if not self._fix_dpkg():
                    print(self._colorize('  Skipping apt (dpkg is broken — see above)', Color.YELLOW))
                    return None
                # Try deadsnakes PPA first (Ubuntu), then default repos
                env = os.environ.copy()
                env['DEBIAN_FRONTEND'] = 'noninteractive'
                # Install software-properties-common for add-apt-repository
                subprocess.run(
                    [*_sudo(), 'apt-get', 'install', '-y', '-qq',
                     'software-properties-common'],
                    timeout=120, env=env,
                )
                subprocess.run(
                    [*_sudo(), 'add-apt-repository', '-y', 'ppa:deadsnakes/ppa'],
                    timeout=120, env=env,
                )
                subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'],
                               timeout=120, env=env)
                self._run_command(
                    [*_sudo(), 'apt-get', 'install', '-y', '-qq',
                     'python3.11', 'python3.11-venv', 'python3.11-dev'],
                    timeout=300,
                )

            elif pkg == 'dnf':
                self._run_command(
                    [*_sudo(), 'dnf', 'install', '-y', '-q',
                     'python3.11', 'python3.11-devel'],
                    timeout=300,
                )

            elif pkg == 'pacman':
                self._run_command(
                    [*_sudo(), 'pacman', '-Sy', '--noconfirm', '--needed', 'python'],
                    timeout=300,
                )

            elif pkg == 'choco':
                if not self._ensure_chocolatey():
                    return None
                self._run_command(
                    ['choco', 'install', 'python311', '-y', '--no-progress'],
                    timeout=600,
                )
                self._refresh_windows_path()

            # Find the new python3.11 binary
            for candidate in ['python3.11', 'python3']:
                binary = shutil.which(candidate)
                if not binary:
                    continue
                try:
                    result = subprocess.run(
                        [binary, '--version'],
                        capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0:
                        ver = result.stdout.strip()
                        parts = ver.split()[-1].split('.')
                        if int(parts[0]) >= 3 and int(parts[1]) >= 11:
                            print(self._colorize(f'✓ {ver} installed', Color.GREEN))
                            return binary
                except Exception:
                    continue

            print(self._colorize('  Python 3.11+ install failed.', Color.RED))
            print(self._colorize(
                '  Install manually from https://python.org/downloads', Color.YELLOW))
            return None
        except Exception as e:
            print(self._colorize(f'  Error installing Python: {e}', Color.RED))
            return None

    # ------------------------------------------------------------------
    # System prerequisites (build tools, libraries)
    # ------------------------------------------------------------------

    def install_system_prerequisites(self) -> bool:
        """Install system build tools and libraries needed by pip packages.

        Runs on ALL platforms (Linux, macOS, Windows) to install everything
        that could fail later: build tools, headers, Python venv, etc.
        One upfront pass prevents surprises in individual install steps.
        """
        pkg = self._detect_package_manager()
        if not pkg:
            return True

        # Fix broken dpkg state before any apt operations
        if pkg == 'apt':
            if not self._fix_dpkg():
                print(self._colorize('  Skipping apt prerequisites (dpkg broken)', Color.YELLOW))
                return True  # Don't block pipeline — fallbacks may still work

        print(self._colorize('⚙️  Installing system prerequisites...', Color.YELLOW))
        try:
            if pkg == 'brew':
                # Ensure Homebrew itself is available
                if not self._ensure_homebrew():
                    return False
                # Xcode Command Line Tools (needed for compiling C extensions)
                subprocess.run(
                    ['xcode-select', '--install'],
                    capture_output=True, timeout=10,
                )
                # Core build libraries that pip packages need
                for formula in ['openssl', 'libffi', 'libpq', 'pkg-config']:
                    subprocess.run(
                        ['brew', 'install', formula],
                        capture_output=True, timeout=120,
                    )
                # Ensure brew's openssl/libpq are findable by pip
                for lib in ['openssl', 'libpq']:
                    prefix = subprocess.run(
                        ['brew', '--prefix', lib],
                        capture_output=True, text=True, timeout=10,
                    )
                    if prefix.returncode == 0 and prefix.stdout.strip():
                        lib_path = prefix.stdout.strip()
                        os.environ['LDFLAGS'] = os.environ.get('LDFLAGS', '') + f' -L{lib_path}/lib'
                        os.environ['CPPFLAGS'] = os.environ.get('CPPFLAGS', '') + f' -I{lib_path}/include'
                        os.environ['PKG_CONFIG_PATH'] = (
                            os.environ.get('PKG_CONFIG_PATH', '') + f':{lib_path}/lib/pkgconfig'
                        )

            elif pkg == 'choco':
                # Ensure Chocolatey itself is available
                if not self._ensure_chocolatey():
                    return False
                # Visual C++ Build Tools (needed for compiling C extensions)
                # Install silently — if already present, choco skips it
                subprocess.run(
                    ['choco', 'install', 'visualstudio2022-workload-vctools', '-y', '--no-progress'],
                    capture_output=True, timeout=600,
                )
                # Git (many tools assume it's available)
                if not self._is_command_available('git'):
                    subprocess.run(
                        ['choco', 'install', 'git', '-y', '--no-progress'],
                        capture_output=True, timeout=300,
                    )
                    self._refresh_windows_path()

            elif pkg == 'apt':
                subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
                self._run_command([
                    *_sudo(), 'apt-get', 'install', '-y', '-qq',
                    # Core tools
                    'curl', 'wget', 'git', 'ca-certificates', 'gnupg',
                    # Build toolchain (needed by pip packages with C extensions)
                    'build-essential', 'gcc', 'g++', 'make', 'pkg-config',
                    # Python venv & dev headers
                    'python3-venv', f'python{py_ver}-venv',
                    'python3-dev', 'python3-pip',
                    # Libraries required by backend requirements.txt
                    'libpq-dev',        # psycopg2
                    'libffi-dev',       # cryptography / cffi
                    'libssl-dev',       # cryptography
                ], timeout=300)

            elif pkg == 'dnf':
                self._run_command([
                    *_sudo(), 'dnf', 'install', '-y', '-q',
                    'curl', 'wget', 'git', 'ca-certificates',
                    'gcc', 'gcc-c++', 'make', 'pkgconfig',
                    'python3-devel', 'python3-pip',
                    'libpq-devel',
                    'libffi-devel',
                    'openssl-devel',
                ], timeout=300)

            elif pkg == 'pacman':
                self._run_command([
                    *_sudo(), 'pacman', '-Sy', '--noconfirm', '--needed',
                    'curl', 'wget', 'git', 'base-devel',
                    'python', 'python-pip',
                    'postgresql-libs',
                    'libffi',
                    'openssl',
                ], timeout=300)

            print(self._colorize('✓ System prerequisites installed', Color.GREEN))
            return True
        except Exception as e:
            print(self._colorize(f'  Warning: Some prerequisites may not have installed: {e}', Color.YELLOW))
            return False

    # ------------------------------------------------------------------
    # Node.js
    # ------------------------------------------------------------------

    def install_node(self) -> bool:
        """Install Node.js 20+ via platform package manager."""
        print(self._colorize('⚙️  Node.js not found or too old.', Color.YELLOW))
        if not self._confirm('Install Node.js 20?'):
            return False

        pkg = self._detect_package_manager()
        if not pkg:
            print(self._colorize('  Could not detect package manager', Color.RED))
            return False

        print(self._colorize('  Installing Node.js 20...', Color.GRAY))
        try:
            if pkg == 'brew':
                if not self._ensure_homebrew():
                    return False
                # Try node@20 first, fall back to node@22, then unversioned node
                for formula in ['node@20', 'node@22', 'node']:
                    result = subprocess.run(
                        ['brew', 'install', formula],
                        capture_output=True, timeout=600,
                    )
                    if result.returncode == 0:
                        subprocess.run(['brew', 'link', '--overwrite', formula],
                                       capture_output=True, timeout=30)
                        break
                # Ensure node is on PATH (brew link can silently fail)
                if not self._is_command_available('node'):
                    for node_dir in Path('/opt/homebrew/opt').glob('node@*/bin'):
                        os.environ['PATH'] = str(node_dir) + ':' + os.environ.get('PATH', '')
                        break
                    else:
                        for node_dir in Path('/usr/local/opt').glob('node@*/bin'):
                            os.environ['PATH'] = str(node_dir) + ':' + os.environ.get('PATH', '')
                            break

            elif pkg == 'apt':
                if self._dpkg_broken:
                    print(self._colorize('  Skipping apt (dpkg is broken — see above)', Color.YELLOW))
                else:
                    # Ensure curl is available for NodeSource setup
                    if not self._is_command_available('curl'):
                        subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                        subprocess.run(
                            [*_sudo(), 'apt-get', 'install', '-y', '-qq', 'curl'],
                            timeout=120,
                        )
                    # Remove conflicting old Node.js dev packages that block
                    # NodeSource installs (e.g. libnode-dev from distro Node 12/16).
                    for conflict_pkg in ['libnode-dev', 'libnode72']:
                        subprocess.run(
                            [*_sudo(), 'apt-get', 'remove', '-y', '-qq', conflict_pkg],
                            capture_output=True, timeout=60,
                        )
                    # NodeSource setup — its nodejs package already includes npm,
                    # so do NOT install the separate npm package alongside it.
                    result = subprocess.run(
                        ['bash', '-c', f'curl -fsSL https://deb.nodesource.com/setup_20.x | {_shell_sudo_E()}bash -'],
                        timeout=120,
                    )
                    if result.returncode == 0:
                        self._run_command([*_sudo(), 'apt-get', 'install', '-y', '-qq', 'nodejs'], timeout=300)
                    else:
                        # NodeSource failed — fall back to distro packages (older Node, separate npm)
                        print(self._colorize('  NodeSource setup failed, trying default repos...', Color.YELLOW))
                        subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                        self._run_command([*_sudo(), 'apt-get', 'install', '-y', '-qq', 'nodejs', 'npm'], timeout=300)

            elif pkg == 'dnf':
                # Ensure curl is available for NodeSource setup
                if not self._is_command_available('curl'):
                    subprocess.run(
                        [*_sudo(), 'dnf', 'install', '-y', '-q', 'curl'],
                        timeout=120,
                    )
                result = subprocess.run(
                    ['bash', '-c', f'curl -fsSL https://rpm.nodesource.com/setup_20.x | {_shell_sudo_E()}bash -'],
                    timeout=120,
                )
                if result.returncode != 0:
                    print(self._colorize('  NodeSource setup failed, trying default repos...', Color.YELLOW))
                self._run_command([*_sudo(), 'dnf', 'install', '-y', '-q', 'nodejs'], timeout=300)

            elif pkg == 'pacman':
                self._run_command([*_sudo(), 'pacman', '-Sy', '--noconfirm', '--needed', 'nodejs', 'npm'], timeout=300)

            elif pkg == 'choco':
                if not self._ensure_chocolatey():
                    return False
                # Try nodejs-lts first, fall back to nodejs
                result = subprocess.run(
                    ['choco', 'install', 'nodejs-lts', '-y', '--no-progress'],
                    capture_output=True, timeout=600,
                )
                if result.returncode != 0:
                    subprocess.run(
                        ['choco', 'install', 'nodejs', '-y', '--no-progress'],
                        capture_output=True, timeout=600,
                    )
                self._refresh_windows_path()
                # Also check common install locations if not on PATH
                if not self._is_command_available('node'):
                    for node_path in [
                        Path('C:/Program Files/nodejs'),
                        Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'nodejs',
                        Path(os.environ.get('APPDATA', '')) / 'nvm' / 'current',
                    ]:
                        if (node_path / 'node.exe').exists():
                            os.environ['PATH'] += ';' + str(node_path)
                            break

            # Verify node is actually available AND meets minimum version
            if self._is_command_available('node'):
                try:
                    ver_result = subprocess.run(
                        ['node', '--version'], capture_output=True, text=True, timeout=5,
                    )
                    ver_major = int(ver_result.stdout.strip().lstrip('v').split('.')[0])
                    if ver_major >= NODE_MIN_VERSION[0]:
                        print(self._colorize('✓ Node.js installed', Color.GREEN))
                        return True
                    else:
                        print(self._colorize(
                            f'  Node.js {ver_result.stdout.strip()} found but {NODE_MIN_VERSION[0]}+ required',
                            Color.YELLOW,
                        ))
                except Exception:
                    pass  # Fall through to fallback sources

            # --- Fallback sources ---
            print(self._colorize('  Primary install failed, trying alternative sources...', Color.YELLOW))

            # Fallback 1: winget (Windows)
            if pkg == 'choco' and self._install_via_winget('OpenJS.NodeJS.LTS'):
                self._refresh_windows_path()
                if self._is_command_available('node'):
                    print(self._colorize('✓ Node.js installed (via winget)', Color.GREEN))
                    return True

            # Fallback 2: snap (Linux)
            if self.platform_name == 'Linux' and self._install_via_snap('node', classic=True):
                if self._is_command_available('node'):
                    print(self._colorize('✓ Node.js installed (via snap)', Color.GREEN))
                    return True

            # Fallback 3: fnm (all platforms — downloads official Node.js binaries)
            if self._install_node_via_fnm():
                print(self._colorize('✓ Node.js installed (via fnm)', Color.GREEN))
                return True

            print(self._colorize('  All Node.js install sources failed.', Color.RED))
            print(self._colorize('  Install manually from https://nodejs.org/en/download/', Color.YELLOW))
            return False
        except Exception as e:
            print(self._colorize(f'  Error installing Node.js: {e}', Color.RED))
            return False

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------

    def _is_postgres_installed(self) -> bool:
        """Check if PostgreSQL is installed (not necessarily running)."""
        if self.platform_name == 'Darwin':
            # Check brew
            for version in ['postgresql@17', 'postgresql@16', 'postgresql@15', 'postgresql']:
                result = subprocess.run(
                    ['brew', 'list', version],
                    capture_output=True, timeout=10,
                )
                if result.returncode == 0:
                    return True
            return False
        elif self.platform_name == 'Windows':
            return (self._is_command_available('psql')
                    or Path('C:/Program Files/PostgreSQL').exists())
        else:
            return self._is_command_available('psql') or self._is_command_available('pg_isready')

    def install_postgres(self) -> bool:
        """Install PostgreSQL 15+ via platform package manager."""
        print(self._colorize('⚙️  PostgreSQL not found.', Color.YELLOW))
        if not self._confirm('Install PostgreSQL?'):
            return False

        pkg = self._detect_package_manager()
        if not pkg:
            print(self._colorize('  Could not detect package manager', Color.RED))
            return False

        print(self._colorize('  Installing PostgreSQL...', Color.GRAY))
        try:
            if pkg == 'brew':
                if not self._ensure_homebrew():
                    return False
                # Try multiple versions — whichever is available in the tap
                installed = False
                for version in ['postgresql@17', 'postgresql@16', 'postgresql@15']:
                    result = subprocess.run(
                        ['brew', 'install', version],
                        capture_output=True, timeout=600,
                    )
                    if result.returncode == 0:
                        subprocess.run(['brew', 'link', '--overwrite', version],
                                       capture_output=True, timeout=30)
                        installed = True
                        break
                if not installed:
                    # Last resort: unversioned formula
                    self._run_command(['brew', 'install', 'postgresql'], timeout=600)
                # Ensure pg binaries are on PATH
                for pg_dir in Path('/opt/homebrew/opt').glob('postgresql@*/bin'):
                    os.environ['PATH'] = str(pg_dir) + ':' + os.environ.get('PATH', '')
                    break
                else:
                    for pg_dir in Path('/usr/local/opt').glob('postgresql@*/bin'):
                        os.environ['PATH'] = str(pg_dir) + ':' + os.environ.get('PATH', '')
                        break

            elif pkg == 'apt':
                if self._dpkg_broken:
                    print(self._colorize('  Skipping apt (dpkg is broken — see above)', Color.YELLOW))
                else:
                    subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                    self._run_command(
                        [*_sudo(), 'apt-get', 'install', '-y', '-qq',
                         'postgresql', 'postgresql-contrib', 'libpq-dev'],
                        timeout=300,
                    )
                    # Ubuntu/Debian: ensure the cluster is created and started.
                    # apt usually does this automatically, but not always
                    # (e.g., when upgrading from an older version).
                    subprocess.run(
                        [*_sudo(), 'systemctl', 'enable', 'postgresql'],
                        capture_output=True, timeout=10,
                    )
                    subprocess.run(
                        [*_sudo(), 'systemctl', 'start', 'postgresql'],
                        capture_output=True, timeout=30,
                    )

            elif pkg == 'dnf':
                self._run_command(
                    [*_sudo(), 'dnf', 'install', '-y', '-q',
                     'postgresql-server', 'postgresql-devel'],
                    timeout=300,
                )
                subprocess.run(
                    [*_sudo(), 'postgresql-setup', '--initdb'],
                    capture_output=True, timeout=60,
                )

            elif pkg == 'pacman':
                self._run_command(
                    [*_sudo(), 'pacman', '-Sy', '--noconfirm', '--needed', 'postgresql'],
                    timeout=300,
                )
                subprocess.run(
                    [*_sudo_user('postgres'), 'initdb', '--locale', 'en_US.UTF-8',
                     '-D', '/var/lib/postgres/data'],
                    capture_output=True, timeout=60,
                )

            elif pkg == 'choco':
                if not self._ensure_chocolatey():
                    return False
                # Try multiple versions
                installed = False
                for pg_ver in ['postgresql17', 'postgresql16', 'postgresql15']:
                    result = subprocess.run(
                        ['choco', 'install', pg_ver, '--params', '/Password:postgres',
                         '-y', '--no-progress'],
                        capture_output=True, timeout=600,
                    )
                    if result.returncode == 0:
                        installed = True
                        break
                if not installed:
                    self._run_command(
                        ['choco', 'install', 'postgresql', '--params', '/Password:postgres',
                         '-y', '--no-progress'],
                        timeout=600,
                    )
                self._refresh_windows_path()
                # Ensure pg binaries are on PATH
                if not self._is_command_available('psql'):
                    pg_base = Path('C:/Program Files/PostgreSQL')
                    if pg_base.exists():
                        for pg_dir in sorted(pg_base.iterdir(), reverse=True):
                            if (pg_dir / 'bin' / 'psql.exe').exists():
                                os.environ['PATH'] += ';' + str(pg_dir / 'bin')
                                break

            # Verify installation
            if self._is_postgres_installed():
                print(self._colorize('✓ PostgreSQL installed', Color.GREEN))
                return True

            # --- Fallback sources ---
            print(self._colorize('  Primary install failed, trying alternative sources...', Color.YELLOW))

            # Fallback: winget (Windows)
            if pkg == 'choco':
                if self._install_via_winget('PostgreSQL.PostgreSQL'):
                    self._refresh_windows_path()
                    if self._is_postgres_installed():
                        print(self._colorize('✓ PostgreSQL installed (via winget)', Color.GREEN))
                        return True

            # Fallback: snap (Linux — not ideal for databases but works)
            if self.platform_name == 'Linux':
                # PostgreSQL via apt.postgresql.org official repo
                if self._dpkg_broken:
                    pass  # Skip apt fallback too — dpkg is broken
                elif self._is_command_available('curl'):
                    print(self._colorize('  Trying official PostgreSQL apt repo...', Color.GRAY))
                    subprocess.run(
                        ['bash', '-c',
                         'curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | '
                         f'{_shell_sudo()}gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg 2>/dev/null'],
                        capture_output=True, timeout=30,
                    )
                    # Get codename
                    codename = subprocess.run(
                        ['bash', '-c', 'lsb_release -cs 2>/dev/null || echo jammy'],
                        capture_output=True, text=True, timeout=5,
                    ).stdout.strip()
                    subprocess.run(
                        ['bash', '-c',
                         f'echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] '
                         f'https://apt.postgresql.org/pub/repos/apt {codename}-pgdg main" | '
                         f'{_shell_sudo()}tee /etc/apt/sources.list.d/pgdg.list'],
                        capture_output=True, timeout=10,
                    )
                    subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                    result = subprocess.run(
                        [*_sudo(), 'apt-get', 'install', '-y', '-qq', 'postgresql', 'postgresql-contrib'],
                        timeout=300,
                    )
                    if result.returncode == 0 and self._is_postgres_installed():
                        print(self._colorize('✓ PostgreSQL installed (via official apt repo)', Color.GREEN))
                        return True

            print(self._colorize('  All PostgreSQL install sources failed.', Color.RED))
            print(self._colorize('  Install manually from https://www.postgresql.org/download/', Color.YELLOW))
            return False
        except Exception as e:
            print(self._colorize(f'  Error installing PostgreSQL: {e}', Color.RED))
            return False

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------

    def _is_redis_installed(self) -> bool:
        """Check if Redis is installed (not necessarily running)."""
        if self.platform_name == 'Darwin':
            result = subprocess.run(
                ['brew', 'list', 'redis'],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        elif self.platform_name == 'Windows':
            # Check both redis-server and memurai (common Windows alternative)
            return (self._is_command_available('redis-server')
                    or self._is_command_available('memurai'))
        else:
            return self._is_command_available('redis-server')

    def install_redis(self) -> bool:
        """Install Redis via platform package manager."""
        print(self._colorize('⚙️  Redis not found.', Color.YELLOW))
        if not self._confirm('Install Redis?'):
            return False

        pkg = self._detect_package_manager()
        if not pkg:
            print(self._colorize('  Could not detect package manager', Color.RED))
            return False

        print(self._colorize('  Installing Redis...', Color.GRAY))
        try:
            if pkg == 'brew':
                if not self._ensure_homebrew():
                    return False
                self._run_command(['brew', 'install', 'redis'], timeout=300)
            elif pkg == 'apt':
                if self._dpkg_broken:
                    print(self._colorize('  Skipping apt (dpkg is broken — see above)', Color.YELLOW))
                else:
                    subprocess.run([*_sudo(), 'apt-get', 'update', '-qq'], timeout=120)
                    self._run_command([*_sudo(), 'apt-get', 'install', '-y', '-qq', 'redis-server'], timeout=300)
            elif pkg == 'dnf':
                self._run_command([*_sudo(), 'dnf', 'install', '-y', '-q', 'redis'], timeout=300)
            elif pkg == 'pacman':
                self._run_command([*_sudo(), 'pacman', '-Sy', '--noconfirm', '--needed', 'redis'], timeout=300)
            elif pkg == 'choco':
                if not self._ensure_chocolatey():
                    return False
                result = subprocess.run(
                    ['choco', 'install', 'redis-64', '-y', '--no-progress'],
                    capture_output=True, timeout=300,
                )
                if result.returncode != 0:
                    # Fallback: Memurai
                    subprocess.run(
                        ['choco', 'install', 'memurai-developer', '-y', '--no-progress'],
                        capture_output=True, timeout=300,
                    )
                self._refresh_windows_path()

            if self._is_redis_installed():
                print(self._colorize('✓ Redis installed', Color.GREEN))
                return True

            # --- Fallback sources ---
            print(self._colorize('  Primary install failed, trying alternative sources...', Color.YELLOW))

            # Fallback: winget (Windows)
            if pkg == 'choco':
                # winget doesn't have Redis; try Memurai via winget
                if self._install_via_winget('Memurai.MemuraiDeveloper'):
                    self._refresh_windows_path()
                    if self._is_redis_installed():
                        print(self._colorize('✓ Redis installed (Memurai via winget)', Color.GREEN))
                        return True

            # Fallback: snap (Linux)
            if self.platform_name == 'Linux':
                if self._install_via_snap('redis'):
                    if self._is_redis_installed():
                        print(self._colorize('✓ Redis installed (via snap)', Color.GREEN))
                        return True

            # Redis is optional — warn but don't fail hard
            print(self._colorize('  Redis install failed (optional — app works without it).', Color.YELLOW))
            return False
        except Exception as e:
            print(self._colorize(f'  Error installing Redis: {e}', Color.RED))
            return False

    # ------------------------------------------------------------------
    # Frontend dependencies
    # ------------------------------------------------------------------

    def install_frontend_deps(self) -> bool:
        """Run npm install in frontend/."""
        print(self._colorize('⚙️  Installing frontend dependencies...', Color.YELLOW))
        try:
            frontend_dir = Path('frontend').resolve()
            # Try strict install first (with retry for network flakiness)
            result = self._retry_command(
                ['npm', 'install'],
                description='npm install',
                timeout=600,
                cwd=str(frontend_dir),
            )
            if result.returncode == 0:
                print(self._colorize('✓ Frontend dependencies installed', Color.GREEN))
                return True

            # Fallback: --legacy-peer-deps to resolve peer dep conflicts
            print(self._colorize('  Retrying with --legacy-peer-deps...', Color.YELLOW))
            result = self._retry_command(
                ['npm', 'install', '--legacy-peer-deps'],
                description='npm install --legacy-peer-deps',
                timeout=600,
                cwd=str(frontend_dir),
            )
            if result.returncode == 0:
                print(self._colorize('✓ Frontend dependencies installed (with legacy peer deps)', Color.GREEN))
                return True

            print(self._colorize('  npm install failed', Color.RED))
            return False
        except Exception as e:
            print(self._colorize(f'  Error installing frontend deps: {e}', Color.RED))
            return False

    # ------------------------------------------------------------------
    # Database setup
    # ------------------------------------------------------------------

    def setup_database(self) -> bool:
        """Create the 'dyslex' PostgreSQL user and database."""
        print(self._colorize('⚙️  Setting up database...', Color.GRAY))
        try:
            if self.platform_name == 'Darwin':
                # macOS: Homebrew PostgreSQL — ensure pg bin is on PATH
                for pg_dir in Path('/opt/homebrew/opt').glob('postgresql@*/bin'):
                    os.environ['PATH'] = str(pg_dir) + ':' + os.environ.get('PATH', '')
                    break
                else:
                    for pg_dir in Path('/usr/local/opt').glob('postgresql@*/bin'):
                        os.environ['PATH'] = str(pg_dir) + ':' + os.environ.get('PATH', '')
                        break

                subprocess.run(['createuser', 'dyslex'], capture_output=True, timeout=10)
                subprocess.run(['createdb', '-O', 'dyslex', 'dyslex'], capture_output=True, timeout=10)
                subprocess.run(
                    ['psql', '-d', 'dyslex', '-c', "ALTER USER dyslex WITH PASSWORD 'dyslex';"],
                    capture_output=True, timeout=10,
                )
            elif self.platform_name == 'Linux':
                subprocess.run(
                    [*_sudo_user('postgres'), 'psql', '-c',
                     "CREATE USER dyslex WITH PASSWORD 'dyslex';"],
                    capture_output=True, timeout=10,
                )
                subprocess.run(
                    [*_sudo_user('postgres'), 'psql', '-c',
                     "CREATE DATABASE dyslex OWNER dyslex;"],
                    capture_output=True, timeout=10,
                )
                subprocess.run(
                    [*_sudo_user('postgres'), 'psql', '-c',
                     "GRANT ALL PRIVILEGES ON DATABASE dyslex TO dyslex;"],
                    capture_output=True, timeout=10,
                )

                # Ubuntu/Debian: pg_hba.conf defaults to 'peer' auth for local
                # connections, which blocks password-based TCP connections that
                # the backend needs (DATABASE_URL uses localhost:5432).
                # Add a rule to allow md5/scram-sha-256 auth for the dyslex user.
                self._configure_pg_hba_for_dyslex()
            elif self.platform_name == 'Windows':
                # Find psql on Windows
                psql_cmd = 'psql'
                if not self._is_command_available('psql'):
                    pg_base = Path('C:/Program Files/PostgreSQL')
                    if pg_base.exists():
                        for pg_dir in sorted(pg_base.iterdir(), reverse=True):
                            psql_path = pg_dir / 'bin' / 'psql.exe'
                            if psql_path.exists():
                                psql_cmd = str(psql_path)
                                os.environ['PATH'] += ';' + str(pg_dir / 'bin')
                                break

                subprocess.run(
                    [psql_cmd, '-U', 'postgres', '-c',
                     "CREATE USER dyslex WITH PASSWORD 'dyslex';"],
                    capture_output=True, timeout=10,
                )
                subprocess.run(
                    [psql_cmd, '-U', 'postgres', '-c',
                     "CREATE DATABASE dyslex OWNER dyslex;"],
                    capture_output=True, timeout=10,
                )

            # Run init.sql to create tables (uses IF NOT EXISTS — safe to re-run)
            init_sql = Path('database/schema/init.sql')
            if init_sql.exists():
                print(self._colorize('  Applying database schema...', Color.GRAY))
                if self.platform_name == 'Darwin':
                    subprocess.run(
                        ['psql', '-U', 'dyslex', '-d', 'dyslex', '-f', str(init_sql)],
                        capture_output=True, timeout=30,
                    )
                elif self.platform_name == 'Linux':
                    # Grant schema permissions first, then run as dyslex user
                    subprocess.run(
                        [*_sudo_user('postgres'), 'psql', '-d', 'dyslex', '-c',
                         'GRANT ALL ON SCHEMA public TO dyslex;'],
                        capture_output=True, timeout=10,
                    )
                    result = subprocess.run(
                        [*_sudo_user('postgres'), 'psql', '-d', 'dyslex',
                         '-f', str(init_sql.resolve())],
                        capture_output=True, timeout=30,
                    )
                    if result.returncode != 0:
                        # Fallback: try with PGPASSWORD
                        env = os.environ.copy()
                        env['PGPASSWORD'] = 'dyslex'
                        subprocess.run(
                            ['psql', '-U', 'dyslex', '-d', 'dyslex', '-h', 'localhost',
                             '-f', str(init_sql.resolve())],
                            capture_output=True, timeout=30, env=env,
                        )
                elif self.platform_name == 'Windows':
                    psql_cmd = 'psql'
                    if not self._is_command_available('psql'):
                        pg_base = Path('C:/Program Files/PostgreSQL')
                        if pg_base.exists():
                            for pg_dir in sorted(pg_base.iterdir(), reverse=True):
                                if (pg_dir / 'bin' / 'psql.exe').exists():
                                    psql_cmd = str(pg_dir / 'bin' / 'psql.exe')
                                    break
                    subprocess.run(
                        [psql_cmd, '-U', 'postgres', '-d', 'dyslex',
                         '-f', str(init_sql.resolve())],
                        capture_output=True, timeout=30,
                    )

            print(self._colorize('✓ Database \'dyslex\' ready (schema applied)', Color.GREEN))
            return True
        except Exception as e:
            print(self._colorize(f'  Warning: Database setup issue: {e}', Color.YELLOW))
            return False

    # ------------------------------------------------------------------
    # pg_hba.conf configuration (Ubuntu/Debian)
    # ------------------------------------------------------------------

    def _configure_pg_hba_for_dyslex(self):
        """Ensure pg_hba.conf allows password auth for the dyslex user over TCP.

        Ubuntu/Debian default pg_hba.conf uses 'peer' auth for local Unix socket
        connections and often has no rule for TCP connections to specific users.
        The backend connects via TCP (localhost:5432) with a password, so we need
        a 'host' line with md5 or scram-sha-256 auth.
        """
        try:
            # Find pg_hba.conf — Debian/Ubuntu stores it under /etc/postgresql/<ver>/main/
            pg_hba = None
            for search_dir in [Path('/etc/postgresql')]:
                if search_dir.exists():
                    for hba in sorted(search_dir.rglob('pg_hba.conf'), reverse=True):
                        pg_hba = hba
                        break
            if not pg_hba:
                return

            # Check if a rule for dyslex already exists
            content = subprocess.run(
                [*_sudo(), 'cat', str(pg_hba)],
                capture_output=True, text=True, timeout=5,
            )
            if content.returncode != 0:
                return

            # Look for an existing rule that covers the dyslex user on localhost
            for line in content.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                if 'dyslex' in stripped and ('md5' in stripped or 'scram-sha-256' in stripped):
                    return  # Already configured

            # Add a rule BEFORE the first 'host' line so it takes priority
            print(self._colorize('  Configuring pg_hba.conf for TCP password auth...', Color.GRAY))
            rule = 'host    dyslex          dyslex          127.0.0.1/32            md5'
            rule_v6 = 'host    dyslex          dyslex          ::1/128                 md5'

            # Insert rules at the top of the host section using a sed command
            subprocess.run(
                [*_sudo(), 'bash', '-c',
                 f'echo "# DysLex AI — allow password auth for dyslex user" >> {pg_hba}\n'
                 f'echo "{rule}" >> {pg_hba}\n'
                 f'echo "{rule_v6}" >> {pg_hba}'],
                capture_output=True, timeout=10,
            )

            # Reload PostgreSQL to pick up the change
            subprocess.run(
                [*_sudo(), 'systemctl', 'reload', 'postgresql'],
                capture_output=True, timeout=10,
            )
            # Also try versioned reload (Debian/Ubuntu)
            try:
                result = subprocess.run(
                    ['pg_lsclusters', '--no-header'],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().splitlines():
                        parts = line.split()
                        if len(parts) >= 3:
                            subprocess.run(
                                [*_sudo(), 'systemctl', 'reload', f'postgresql@{parts[0]}-{parts[1]}'],
                                capture_output=True, timeout=10,
                            )
            except FileNotFoundError:
                pass

            print(self._colorize('  ✓ pg_hba.conf updated for TCP password auth', Color.GREEN))
        except Exception as e:
            print(self._colorize(f'  Warning: Could not configure pg_hba.conf: {e}', Color.YELLOW))
            print(self._colorize(
                '  You may need to manually add this line to pg_hba.conf:\n'
                '    host  dyslex  dyslex  127.0.0.1/32  md5',
                Color.YELLOW,
            ))

    # ------------------------------------------------------------------
    # .env file
    # ------------------------------------------------------------------

    def create_env_file(self) -> bool:
        """Create .env from template if missing."""
        env_file = Path('.env')
        if env_file.exists():
            return True

        print(self._colorize('⚙️  Creating .env file...', Color.GRAY))
        env_content = """# DysLex AI Environment Configuration
# Get your API key at: https://build.nvidia.com
NVIDIA_NIM_API_KEY=

# Database (defaults work with local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET_KEY=change-me-in-production
"""
        atomic_write(env_file, env_content)
        print(self._colorize('✓ .env created — edit it to add your NVIDIA_NIM_API_KEY', Color.GREEN))
        return True


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
        self.created_artifacts: List[Tuple[str, Path]] = []  # For rollback
        self.installer: Optional[PackageInstaller] = None
        self.setup_state: Optional[SetupState] = None
        if self.auto_setup:
            self.installer = PackageInstaller(
                color_enabled=color_enabled,
                yes=config.get('yes', False),
            )
            self.setup_state = SetupState(Path('.dyslex-setup-state.json'))
            if self.setup_state.has_any_progress():
                print(self._colorize(
                    '  Resuming previous auto-setup (some steps already completed)...',
                    Color.CYAN,
                ))

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.color_enabled:
            return text
        return f"{color}{text}{Color.RESET}"

    # ------------------------------------------------------------------
    # Dependency Pre-Scan
    # ------------------------------------------------------------------

    def scan_dependencies(self) -> List[DependencyStatus]:
        """Read-only scan of all dependencies — no installations, only detection.

        Returns a list of DependencyStatus objects describing what is present,
        missing, running, or stopped.
        """
        results: List[DependencyStatus] = []

        # --- Python ---
        version = sys.version_info[:3]
        ver_str = f'{version[0]}.{version[1]}.{version[2]}'
        if version[:2] >= PYTHON_MIN_VERSION:
            results.append(DependencyStatus('Python', DepState.INSTALLED, ver_str))
        else:
            results.append(DependencyStatus(
                'Python', DepState.OUTDATED, ver_str,
                action=f'Need Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+',
            ))

        # --- Node.js ---
        if self.mode in ('dev', 'frontend'):
            try:
                result = subprocess.run(
                    ['node', '--version'],
                    capture_output=True, text=True, timeout=5,
                )
                node_ver = result.stdout.strip().lstrip('v')
                major = int(node_ver.split('.')[0])
                if major >= NODE_MIN_VERSION[0]:
                    results.append(DependencyStatus('Node.js', DepState.INSTALLED, node_ver))
                else:
                    results.append(DependencyStatus(
                        'Node.js', DepState.OUTDATED, node_ver,
                        action=f'Need Node.js {NODE_MIN_VERSION[0]}+',
                    ))
            except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, IndexError):
                # Try nvm fallback (read-only: _find_node_via_nvm updates PATH)
                nvm_node = self._find_node_via_nvm()
                if nvm_node:
                    try:
                        result = subprocess.run(
                            [nvm_node, '--version'],
                            capture_output=True, text=True, timeout=5,
                        )
                        node_ver = result.stdout.strip().lstrip('v')
                        results.append(DependencyStatus('Node.js', DepState.INSTALLED, f'{node_ver} (nvm)'))
                    except Exception:
                        results.append(DependencyStatus(
                            'Node.js', DepState.MISSING,
                            action='Install Node.js 20+',
                        ))
                else:
                    results.append(DependencyStatus(
                        'Node.js', DepState.MISSING,
                        action='Install Node.js 20+',
                    ))

        # --- PostgreSQL ---
        if self.mode in ('dev', 'backend'):
            pg_installed = self.installer._is_postgres_installed() if self.installer else (
                shutil.which('psql') is not None or shutil.which('pg_isready') is not None
            )
            if pg_installed:
                if self._is_port_open('localhost', POSTGRES_PORT):
                    results.append(DependencyStatus('PostgreSQL', DepState.RUNNING))
                else:
                    results.append(DependencyStatus(
                        'PostgreSQL', DepState.STOPPED,
                        action='Start PostgreSQL service',
                    ))
            else:
                results.append(DependencyStatus(
                    'PostgreSQL', DepState.MISSING,
                    action='Install and start PostgreSQL',
                ))

        # --- Redis (optional) ---
        if self.mode in ('dev', 'backend'):
            redis_installed = self.installer._is_redis_installed() if self.installer else (
                shutil.which('redis-server') is not None
            )
            if redis_installed:
                if self._is_port_open('localhost', REDIS_PORT):
                    results.append(DependencyStatus('Redis', DepState.RUNNING, critical=False))
                else:
                    results.append(DependencyStatus(
                        'Redis', DepState.STOPPED,
                        action='Start Redis service',
                        critical=False,
                    ))
            else:
                results.append(DependencyStatus(
                    'Redis', DepState.MISSING,
                    action='Install and start Redis',
                    critical=False,
                ))

        # --- Build tools ---
        if self.installer:
            has_gcc = self.installer._is_command_available('gcc')
            has_make = self.installer._is_command_available('make')
            if has_gcc and has_make:
                results.append(DependencyStatus('Build tools', DepState.INSTALLED))
            else:
                missing = []
                if not has_gcc:
                    missing.append('gcc')
                if not has_make:
                    missing.append('make')
                results.append(DependencyStatus(
                    'Build tools', DepState.MISSING,
                    action=f'Install {", ".join(missing)}',
                ))

        # --- Backend venv ---
        if self.mode in ('dev', 'backend'):
            venv_python = self._find_venv_python()
            if venv_python and venv_python.exists():
                results.append(DependencyStatus('Backend venv', DepState.INSTALLED))
            else:
                results.append(DependencyStatus(
                    'Backend venv', DepState.MISSING,
                    action='Create venv + install pip packages',
                ))

        # --- Frontend deps ---
        if self.mode in ('dev', 'frontend'):
            if Path('frontend/node_modules').exists():
                results.append(DependencyStatus('Frontend deps', DepState.INSTALLED))
            else:
                results.append(DependencyStatus(
                    'Frontend deps', DepState.MISSING,
                    action='Run npm install',
                ))

        # --- .env file (optional) ---
        if Path('.env').exists():
            results.append(DependencyStatus('.env file', DepState.INSTALLED, critical=False))
        else:
            results.append(DependencyStatus(
                '.env file', DepState.MISSING,
                action='Create from template',
                critical=False,
            ))

        return results

    def _print_scan_summary(self, results: List[DependencyStatus]) -> None:
        """Print a color-coded dependency scan table."""
        print(f"\n{self._colorize('  Dependency Pre-Scan:', Color.BOLD)}\n")

        # Find the longest dependency name for alignment
        max_name = max(len(r.name) for r in results)

        for r in results:
            # Padded name + dotted leader
            dots = '.' * (max_name + 4 - len(r.name))
            name_part = f'    {r.name} {dots}'

            # Version column (fixed width)
            ver_part = f'{r.version:<14}'

            # State + action
            state_val = r.state.value
            if r.state in (DepState.INSTALLED, DepState.RUNNING):
                state_color = Color.GREEN
                action_part = ''
            elif r.state == DepState.STOPPED:
                state_color = Color.YELLOW
                action_part = f' -> {r.action}' if r.action else ''
            else:
                state_color = Color.RED
                action_part = f' -> {r.action}' if r.action else ''

            state_part = self._colorize(state_val, state_color)

            print(f'{name_part} {ver_part}{state_part}{action_part}')

        # Summary counts
        needs_action = [r for r in results if r.state not in (DepState.INSTALLED, DepState.RUNNING)]
        required = [r for r in needs_action if r.critical]
        optional = [r for r in needs_action if not r.critical]

        if needs_action:
            print()
            if required:
                names = ', '.join(r.name for r in required)
                print(self._colorize(
                    f'  {len(required)} required to install: {names}',
                    Color.YELLOW,
                ))
            if optional:
                names = ', '.join(r.name for r in optional)
                print(self._colorize(
                    f'  {len(optional)} optional: {names}',
                    Color.GRAY,
                ))
        print()

    def _confirm_scan(self, results: List[DependencyStatus]) -> bool:
        """Ask the user to confirm before installing scanned dependencies.

        Returns True if:
        - All deps are already satisfied (no prompt needed)
        - --yes flag or non-interactive mode (auto-confirmed)
        - --check-only mode (scan shown but nothing to install)
        - User answers Y/yes/Enter
        """
        needs_action = any(
            r.state not in (DepState.INSTALLED, DepState.RUNNING)
            for r in results
        )
        if not needs_action:
            return True

        # In --check-only mode, show the scan but don't prompt
        if self.config.get('check_only', False):
            return True

        # --yes flag
        if self.config.get('yes', False):
            print(self._colorize(
                '  Proceeding with install (auto-confirmed with --yes)',
                Color.GRAY,
            ))
            return True

        # Non-interactive
        if not sys.stdin.isatty():
            print(self._colorize(
                '  Proceeding with install (auto-confirmed: non-interactive mode)',
                Color.GRAY,
            ))
            return True

        # Interactive prompt
        try:
            answer = input('  Proceed with installing the above? [Y/n] ').strip().lower()
            if answer in ('', 'y', 'yes'):
                return True
            print(self._colorize('  Aborted by user.', Color.YELLOW))
            return False
        except (EOFError, KeyboardInterrupt):
            print()
            return False

    def check_all(self) -> bool:
        """Run all applicable checks. Returns True if all critical checks pass.

        Check order is dependency-aware:
        0. Dependency pre-scan (read-only summary + user confirmation)
        1. Pre-flight checks (disk space, network, sudo)
        2. Python version (always first — we're running in it)
        3. Node.js (needed before frontend deps)
        4. PostgreSQL (install → start → database setup)
        5. Redis (install → start)
        6. Backend dependencies (venv)
        7. Backend port
        8. Frontend dependencies (npm install)
        9. Frontend port
        10. Environment file (.env)
        11. Environment variables (NVIDIA key prompt)
        12. NVIDIA NIM API ping
        """
        # --- Dependency pre-scan: show what needs installing before doing anything ---
        if self.auto_setup and self.mode != 'docker':
            scan_results = self.scan_dependencies()
            self._print_scan_summary(scan_results)
            if not self._confirm_scan(scan_results):
                return False  # user declined

            # Only run preflight (disk/network/sudo) if something needs installing
            needs_install = any(
                r.state not in (DepState.INSTALLED, DepState.RUNNING)
                for r in scan_results
            )
            if needs_install:
                self.preflight_checks()

        # Install system build tools & libraries upfront on Linux
        if self.auto_setup and self.installer and self.mode != 'docker':
            if not self.setup_state or not self.setup_state.is_step_done('system_prerequisites'):
                self.installer.install_system_prerequisites()
                if self.setup_state:
                    self.setup_state.mark_done('system_prerequisites')

        checks = [
            ("Python version", self.check_python_version),
        ]

        if self.mode == 'docker':
            checks.append(("Docker availability", self.check_docker_availability))
        else:
            # Node.js is needed by both frontend-only and dev modes
            if self.mode in ['dev', 'frontend']:
                checks.append(("Node.js version", self.check_node_version))

            # Development mode checks — services
            if self.mode in ['dev', 'backend']:
                checks.extend([
                    ("PostgreSQL service", self.check_postgres_service),
                    ("Database setup", self.check_database_setup),
                    ("Redis service", self.check_redis_service),
                    ("Backend dependencies", self.check_backend_dependencies),
                    ("Backend port availability", self.check_backend_port),
                ])

            if self.mode in ['dev', 'frontend']:
                checks.extend([
                    ("Frontend dependencies", self.check_frontend_dependencies),
                    ("Frontend port availability", self.check_frontend_port),
                ])

        # Environment file (create .env before prompting for variables)
        checks.append(("Environment file", self.check_env_file))

        # Environment variables (warning only)
        checks.append(("Environment variables", self.check_environment_variables))

        # NVIDIA NIM API connectivity (warning only, runs after env vars so key is available)
        checks.append(("NVIDIA NIM API", self.check_nvidia_api))

        # Run all checks
        # Maximum attempts before showing diagnostic help instead of retrying
        MAX_STEP_ATTEMPTS = 3

        for name, check_func in checks:
            # Track attempt counts for auto-setup steps
            if self.auto_setup and self.setup_state:
                step_key = name.lower().replace(' ', '_')
                if not self.setup_state.is_step_done(step_key):
                    attempts = self.setup_state.increment_attempt(step_key)
                    if attempts > MAX_STEP_ATTEMPTS:
                        self.errors.append((name,
                            f'"{name}" has failed {attempts - 1} times across runs.\n'
                            f'    This step may need manual intervention:\n'
                            f'    1. Check the error messages from previous runs above\n'
                            f'    2. Try running the step manually (see docs)\n'
                            f'    3. Delete .dyslex-setup-state.json to reset all counters'
                        ))
                        continue

            try:
                check_func()
            except CheckError as e:
                self.errors.append((name, str(e)))
            except CheckWarning as e:
                self.warnings.append((name, str(e)))
            except CheckSkipped:
                pass

        if self.errors and self.auto_setup:
            self.rollback()

        # On full success, clear the setup state file
        if not self.errors and self.setup_state:
            self.setup_state.clear()

        return len(self.errors) == 0

    def preflight_checks(self):
        """Run pre-flight checks before starting auto-setup.

        Warns about potential issues that would cause installs to fail:
        - Low disk space
        - No network connectivity to package registries
        - Missing sudo access (Linux only, skipped when running as root)
        """
        # --- Disk space ---
        try:
            usage = shutil.disk_usage(Path('.').resolve())
            free_gb = usage.free / (1024 ** 3)
            if free_gb < 1:
                raise CheckError(
                    f"Only {free_gb:.1f}GB disk space free — auto-setup requires at least 1GB\n"
                    f"    PyTorch CPU-only alone needs ~800MB-2GB. Free up disk space and retry."
                )
            elif free_gb < 2:
                print(self._colorize(
                    f'  Warning: Only {free_gb:.1f}GB disk space free. '
                    f'Auto-setup needs at least 2GB (5GB recommended).',
                    Color.YELLOW,
                ))
            elif free_gb < 5:
                print(self._colorize(
                    f'  Note: {free_gb:.1f}GB disk space free. '
                    f'5GB recommended for full backend + ML packages.',
                    Color.YELLOW,
                ))
        except CheckError:
            raise
        except Exception:
            pass

        # --- Network connectivity ---
        unreachable_registries = []
        for host, port, label in [
            ('pypi.org', 443, 'PyPI (Python packages)'),
            ('registry.npmjs.org', 443, 'npm (Node packages)'),
        ]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((host, port))
            except (socket.timeout, ConnectionRefusedError, OSError):
                unreachable_registries.append(label)
                print(self._colorize(
                    f'  Warning: Cannot reach {label} ({host}:{port}). '
                    f'Package installs may fail.',
                    Color.YELLOW,
                ))

        if len(unreachable_registries) >= 2:
            raise CheckError(
                "Cannot reach any package registries (PyPI and npm are both unreachable)\n"
                "    Auto-setup requires network access to download packages.\n"
                "    Check your internet connection and retry."
            )

        # --- Sudo access (Linux only, skip if already root) ---
        if self.platform_name == 'Linux' and not IS_ROOT:
            try:
                result = subprocess.run(
                    ['sudo', '-v'],
                    timeout=30,
                )
                if result.returncode != 0:
                    print(self._colorize(
                        '  Warning: sudo access not available. '
                        'Some system packages may fail to install.',
                        Color.YELLOW,
                    ))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print(self._colorize(
                    '  Warning: sudo not found or timed out.',
                    Color.YELLOW,
                ))

    def rollback(self):
        """Clean up artifacts created during a failed auto-setup.

        - Removes broken venv directories
        - Stops auto-started services
        - Clears setup state so next run starts fresh
        - Does NOT remove .env (may contain user-entered API keys)
        - Does NOT remove node_modules (safe to re-run npm install)
        """
        if not self.auto_setup:
            return

        print(self._colorize('\n  Cleaning up after failed auto-setup...', Color.YELLOW))

        # Remove created artifacts (broken venv dirs)
        for artifact_type, artifact_path in self.created_artifacts:
            if artifact_type == 'venv' and artifact_path.exists():
                print(self._colorize(f'  Removing broken {artifact_path}...', Color.GRAY))
                try:
                    shutil.rmtree(artifact_path)
                except Exception as e:
                    print(self._colorize(f'  Warning: Could not remove {artifact_path}: {e}', Color.YELLOW))

        # Stop any auto-started services
        self.cleanup_started_services()

        # Clear setup state so next run starts fresh
        if self.setup_state:
            self.setup_state.clear()

    def _find_suitable_python(self) -> Optional[str]:
        """Search for an already-installed Python >= PYTHON_MIN_VERSION.

        Checks versioned binaries like python3.13, python3.12, python3.11
        (highest first) so we pick the best available interpreter.
        Returns the absolute path if found, None otherwise.
        """
        # Check from highest to lowest so we prefer the newest version
        for minor in range(15, PYTHON_MIN_VERSION[1] - 1, -1):
            candidate = f'python3.{minor}'
            binary = shutil.which(candidate)
            if not binary:
                continue
            try:
                result = subprocess.run(
                    [binary, '--version'],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    ver_str = result.stdout.strip().split()[-1]
                    parts = ver_str.split('.')
                    if int(parts[0]) >= 3 and int(parts[1]) >= PYTHON_MIN_VERSION[1]:
                        return binary
            except Exception:
                continue
        return None

    def check_python_version(self):
        """Verify Python version is 3.11+. Install if missing and auto_setup.

        When the current interpreter is too old, this method first searches
        for an already-installed suitable Python (e.g. python3.11, python3.12)
        before attempting to install one. If a suitable binary is found, the
        script re-execs under it via os.execv() — same terminal, same
        arguments, seamless switchover.
        """
        version = sys.version_info[:2]
        if version < PYTHON_MIN_VERSION:
            # Before installing anything, check if a suitable Python is
            # already on the system (e.g. python3.11 exists but python3
            # points to an older version).
            existing = self._find_suitable_python()
            if existing:
                script = os.path.abspath(sys.argv[0])
                print(f"\n{Color.CYAN}  Found {existing} — restarting under it...{Color.RESET}\n")
                os.execv(existing, [existing, script] + sys.argv[1:])

            if self.auto_setup and self.installer:
                new_python = self.installer.install_python()
                if new_python:
                    # Re-exec this script under the new Python in-place.
                    # os.execv replaces the current process — same PID,
                    # same terminal, user sees no interruption.
                    script = os.path.abspath(sys.argv[0])
                    print(f"\n{Color.CYAN}  Restarting under {new_python}...{Color.RESET}\n")
                    os.execv(new_python, [new_python, script] + sys.argv[1:])
                raise CheckError(
                    f"Failed to install Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ automatically\n"
                    f"    Fix: Install Python 3.11+ manually: https://python.org/downloads"
                )
            raise CheckError(
                f"Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ required, found {version[0]}.{version[1]}\n"
                f"    Fix: Install Python 3.11+: https://python.org/downloads\n"
                f"    Or use: python3 run.py --auto-setup"
            )

    def _find_node_via_nvm(self) -> Optional[str]:
        """Try to find a Node.js >= NODE_MIN_VERSION via nvm.

        Checks common nvm directories for installed versions and, if a
        suitable version is found, adds it to PATH so subsequent
        subprocess calls use it.  Returns the node binary path on
        success, None otherwise.
        """
        nvm_dirs = [
            os.environ.get('NVM_DIR', ''),
            os.path.expanduser('~/.nvm'),
            '/usr/local/nvm',
        ]
        for nvm_dir in nvm_dirs:
            if not nvm_dir or not os.path.isdir(nvm_dir):
                continue
            versions_dir = os.path.join(nvm_dir, 'versions', 'node')
            if not os.path.isdir(versions_dir):
                continue
            # Collect installed versions, pick the best one >= minimum
            candidates: List[Tuple[int, str]] = []
            for entry in os.listdir(versions_dir):
                ver_str = entry.lstrip('v')
                try:
                    major = int(ver_str.split('.')[0])
                except (ValueError, IndexError):
                    continue
                if major >= NODE_MIN_VERSION[0]:
                    bin_path = os.path.join(versions_dir, entry, 'bin')
                    node_bin = os.path.join(bin_path, 'node')
                    if os.path.isfile(node_bin):
                        candidates.append((major, bin_path))
            if candidates:
                # Use the highest available version
                candidates.sort(reverse=True)
                best_bin_dir = candidates[0][1]
                os.environ['PATH'] = best_bin_dir + ':' + os.environ.get('PATH', '')
                return os.path.join(best_bin_dir, 'node')
        return None

    def check_node_version(self):
        """Verify Node.js version is 20+. Install if missing and auto_setup."""
        need_install = False
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
                need_install = True
        except FileNotFoundError:
            need_install = True
        except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
            raise CheckError(f"Could not determine Node.js version: {e}")

        if need_install:
            # Before installing, check if a suitable version is already
            # available via nvm but just not the active selection.
            nvm_node = self._find_node_via_nvm()
            if nvm_node:
                try:
                    result = subprocess.run(
                        [nvm_node, '--version'],
                        capture_output=True, text=True, timeout=5,
                    )
                    ver = result.stdout.strip().lstrip('v')
                    print(f"{self._colorize(f'  Found Node.js v{ver} via nvm — using it', Color.GREEN)}")
                    return  # PATH already updated by _find_node_via_nvm
                except Exception:
                    pass  # Fall through to install

            if self.auto_setup and self.installer:
                if self.installer.install_node():
                    return  # Successfully installed
                raise CheckError(
                    "Failed to install Node.js automatically\n"
                    "    Fix: Install Node.js 20+ manually: https://nodejs.org"
                )
            raise CheckError(
                "Node.js 20+ not found\n"
                "    Fix: Install Node.js 20+: https://nodejs.org\n"
                "    Or use: python3 run.py --auto-setup"
            )

    def check_postgres_service(self):
        """Check if PostgreSQL is installed and running on localhost:5432."""
        # First check if PostgreSQL is installed at all
        if self.auto_setup and self.installer and not self.installer._is_postgres_installed():
            if not self.installer.install_postgres():
                raise CheckError(
                    "Failed to install PostgreSQL automatically\n"
                    "    Fix: Install PostgreSQL 15+ manually"
                )

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
        """Check if Redis is installed and running on localhost:6379 (warning only)."""
        # First check if Redis is installed at all
        if self.auto_setup and self.installer and not self.installer._is_redis_installed():
            if not self.installer.install_redis():
                raise CheckWarning(
                    "Failed to install Redis automatically\n"
                    "    Note: Redis is optional but recommended for snapshot storage"
                )

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
            if not sys.stdin.isatty():
                print(f"   {self._colorize('Non-interactive mode: set NVIDIA_NIM_API_KEY env var before running.', Color.GRAY)}")
                key = ""
            else:
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
                atomic_write(env_file, '\n'.join(lines) + '\n')
                print(f"   {self._colorize('✓ API key saved to .env', Color.GREEN)}")
            else:
                raise CheckWarning(
                    "NVIDIA_NIM_API_KEY not set (skipped)\n"
                    "    Note: Some features (LLM corrections, TTS) will not work without it"
                )

    def check_nvidia_api(self):
        """Ping NVIDIA NIM models to verify the API key works."""
        api_key = os.getenv('NVIDIA_NIM_API_KEY')
        if not api_key:
            raise CheckSkipped()

        base_url = os.getenv('NVIDIA_NIM_LLM_URL', NVIDIA_NIM_BASE_URL)

        print(f"\n{self._colorize('🔌 Pinging NVIDIA NIM models...', Color.CYAN)}")

        failures = []
        for model_id, description in NVIDIA_NIM_MODELS:
            try:
                url = f"{base_url}/chat/completions"
                payload = json.dumps({
                    "model": model_id,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }).encode('utf-8')

                req = Request(url, data=payload, method='POST')
                req.add_header('Authorization', f'Bearer {api_key}')
                req.add_header('Content-Type', 'application/json')

                with urlopen(req, timeout=NVIDIA_NIM_PING_TIMEOUT) as response:
                    print(f"   {self._colorize('✓', Color.GREEN)} {model_id} — {description}")

            except HTTPError as e:
                code = e.code
                # Try to extract detail from response body
                detail = ''
                try:
                    body = e.read().decode('utf-8', errors='replace')
                    parsed = json.loads(body)
                    detail = parsed.get('detail', '') or parsed.get('message', '')
                except Exception:
                    pass

                if code == 401:
                    reason = "Invalid API key (401 Unauthorized)"
                elif code == 403:
                    reason = "Access denied (403 Forbidden)"
                elif code == 404:
                    reason = f"Model not found (404)"
                else:
                    reason = f"HTTP {code}"
                    if detail:
                        reason += f" — {detail}"

                print(f"   {self._colorize('✗', Color.RED)} {model_id} — {reason}")
                failures.append((model_id, reason))

            except URLError as e:
                reason = str(e.reason) if hasattr(e, 'reason') else str(e)

                print(f"   {self._colorize('✗', Color.RED)} {model_id} — {reason}")
                failures.append((model_id, reason))

            except Exception as e:
                reason = str(e)
                print(f"   {self._colorize('✗', Color.RED)} {model_id} — {reason}")
                failures.append((model_id, reason))

        if failures:
            failed_names = ", ".join(m for m, _ in failures)
            first_error = failures[0][1]
            raise CheckWarning(
                f"Could not reach NVIDIA NIM model(s): {failed_names}\n"
                f"    Error: {first_error}\n"
                f"    Note: LLM corrections, brainstorm, and vision features require working API access"
            )

    def check_backend_dependencies(self):
        """Verify backend virtual environment and dependencies are installed."""
        backend_dir = Path('backend')
        venv_python = self._find_venv_python()

        if not venv_python or not venv_python.exists():
            if self.auto_setup:
                # Check if venv steps are already done from a previous run
                if self.setup_state and self.setup_state.is_step_done('pip_heavy_packages'):
                    # State says done but venv is missing — stale state, reset
                    if self.setup_state:
                        self.setup_state.clear()

                print(f"{self._colorize('⚙️  Creating backend virtual environment...', Color.YELLOW)}")
                if self._create_backend_venv():
                    print(f"{self._colorize('✓ Backend venv created and dependencies installed', Color.GREEN)}")
                    if self.setup_state:
                        self.setup_state.mark_done('venv_create')
                        self.setup_state.mark_done('pip_light_packages')
                        self.setup_state.mark_done('pip_heavy_packages')
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
        """Verify frontend node_modules are installed. Auto-install if auto_setup."""
        node_modules = Path('frontend/node_modules')
        if not node_modules.exists():
            if self.auto_setup and self.installer:
                if self.setup_state and self.setup_state.is_step_done('npm_install'):
                    # State says done but node_modules is missing — stale state
                    pass  # Fall through to re-install
                if self.installer.install_frontend_deps():
                    if self.setup_state:
                        self.setup_state.mark_done('npm_install')
                    return
                raise CheckError(
                    "Failed to install frontend dependencies automatically\n"
                    "    Fix: cd frontend && npm install"
                )
            raise CheckError(
                "Frontend dependencies not installed\n"
                "    Fix: cd frontend && npm install\n"
                "    Or use: python3 run.py --auto-setup"
            )

    def check_database_setup(self):
        """Verify the 'dyslex' database and user exist. Create if auto_setup."""
        if not self.auto_setup:
            # Without auto_setup, we just check connectivity via the port
            # (the backend will fail with a clear error if the DB doesn't exist)
            return

        if self.installer:
            self.installer.setup_database()

    def check_env_file(self):
        """Create .env from template if missing and auto_setup is enabled."""
        if not self.auto_setup:
            return

        if self.installer:
            self.installer.create_env_file()
            if self.setup_state:
                self.setup_state.mark_done('env_file')

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
            if self.auto_setup or self.kill_ports:
                print(f"{self._colorize(f'⚙️  Killing process on port {port}...', Color.YELLOW)}")
                if self._kill_port_process(port):
                    print(f"{self._colorize(f'✓ Port {port} freed', Color.GREEN)}")
                else:
                    raise CheckError(
                        f"Port {port} is already in use and could not be freed\n"
                        f"    Fix: Stop the existing process manually or use --port-backend <port>"
                    )
            else:
                raise CheckError(
                    f"Port {port} is already in use\n"
                    f"    Fix: Stop the existing process, use --port-backend <port>, or use --kill-ports"
                )

    def check_frontend_port(self):
        """Check if frontend port is available."""
        port = self.config.get('frontend_port', DEFAULT_FRONTEND_PORT)
        if not self._is_port_available(port):
            if self.auto_setup or self.kill_ports:
                print(f"{self._colorize(f'⚙️  Killing process on port {port}...', Color.YELLOW)}")
                if self._kill_port_process(port):
                    print(f"{self._colorize(f'✓ Port {port} freed', Color.GREEN)}")
                else:
                    raise CheckError(
                        f"Port {port} is already in use and could not be freed\n"
                        f"    Fix: Stop the existing process manually or use --port-frontend <port>"
                    )
            else:
                raise CheckError(
                    f"Port {port} is already in use\n"
                    f"    Fix: Stop the existing process, use --port-frontend <port>, or use --kill-ports"
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
            return "Start PostgreSQL: brew services start postgresql@15  (or @16, @17)"
        elif self.platform_name == 'Linux':
            return "Start PostgreSQL: sudo systemctl start postgresql" if not IS_ROOT else "Start PostgreSQL: systemctl start postgresql"
        else:  # Windows
            return "Start PostgreSQL: net start postgresql-x64-15  (or open Services panel)"

    def _get_redis_start_command(self) -> str:
        """Get the Redis start command for the current platform."""
        if self.platform_name == 'Darwin':  # macOS
            return "Start Redis: brew services start redis"
        elif self.platform_name == 'Linux':
            return "Start Redis: sudo systemctl start redis-server  (or redis)" if not IS_ROOT else "Start Redis: systemctl start redis-server  (or redis)"
        else:  # Windows
            return "Start Redis: Download from https://redis.io/download or use Docker"

    def _start_postgres(self) -> bool:
        """Attempt to start PostgreSQL service."""
        try:
            if self.platform_name == 'Darwin':  # macOS
                # Try all versioned formulae then unversioned
                for svc_name in ['postgresql@17', 'postgresql@16', 'postgresql@15', 'postgresql']:
                    result = subprocess.run(
                        ['brew', 'services', 'start', svc_name],
                        capture_output=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        break
                # Wait for service to start
                time.sleep(3)
                return self._verify_postgres_connection()

            elif self.platform_name == 'Linux':
                started = False
                is_debian = False

                # Step 1: Detect installed clusters via pg_lsclusters (Debian/Ubuntu)
                detected_clusters = []
                try:
                    result = subprocess.run(
                        ['pg_lsclusters', '--no-header'],
                        capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0:
                        is_debian = True
                        for line in result.stdout.strip().splitlines():
                            parts = line.split()
                            if len(parts) >= 3:
                                ver, name, status = parts[0], parts[1], parts[2]
                                detected_clusters.append((ver, name, status))
                except FileNotFoundError:
                    pass  # Not a Debian/Ubuntu system

                # Step 2: Try starting detected clusters
                if detected_clusters:
                    for ver, name, status in detected_clusters:
                        if status == 'online':
                            started = True
                            break
                        # Try systemctl first
                        result = subprocess.run(
                            [*_sudo(), 'systemctl', 'start', f'postgresql@{ver}-{name}'],
                            capture_output=True, text=True, timeout=30,
                        )
                        if result.returncode == 0:
                            started = True
                            break
                        # Try pg_ctlcluster
                        result = subprocess.run(
                            [*_sudo(), 'pg_ctlcluster', ver, name, 'start'],
                            capture_output=True, text=True, timeout=30,
                        )
                        if result.returncode == 0:
                            started = True
                            break

                    # Step 2b: If starting failed, the cluster is likely broken.
                    # Drop it and recreate — this fixes "service did not take the
                    # steps required by its unit configuration" on Ubuntu.
                    if not started:
                        for ver, name, status in detected_clusters:
                            print(f"{self._colorize(f'  Cluster {ver}/{name} failed to start. Recreating...', Color.YELLOW)}")
                            subprocess.run(
                                [*_sudo(), 'pg_dropcluster', '--stop', ver, name],
                                capture_output=True, timeout=30,
                            )
                            result = subprocess.run(
                                [*_sudo(), 'pg_createcluster', ver, name, '--start'],
                                capture_output=True, text=True, timeout=60,
                            )
                            if result.returncode == 0:
                                print(f"{self._colorize(f'  Cluster {ver}/{name} recreated and started', Color.GREEN)}")
                                started = True
                                break
                            else:
                                print(f"{self._colorize(f'  pg_createcluster failed: {result.stderr.strip()}', Color.YELLOW)}")

                # Step 3: No clusters detected or not Debian — try common service names
                # (Fedora/Arch use plain 'postgresql')
                if not started and not is_debian:
                    for svc_name in ['postgresql']:
                        result = subprocess.run(
                            [*_sudo(), 'systemctl', 'start', svc_name],
                            timeout=30,
                        )
                        if result.returncode == 0:
                            started = True
                            break

                # Step 4: Fallback — start directly as postgres user via pg_ctl
                # (useful in Docker containers without systemd)
                if not started:
                    for data_dir in [
                        Path('/var/lib/postgresql/14/main'),
                        Path('/var/lib/postgresql/15/main'),
                        Path('/var/lib/postgresql/16/main'),
                        Path('/var/lib/postgresql/17/main'),
                    ]:
                        if data_dir.exists():
                            result = subprocess.run(
                                [*_sudo_user('postgres'),
                                 'pg_ctl', 'start', '-D', str(data_dir),
                                 '-l', '/var/log/postgresql/startup.log', '-w'],
                                capture_output=True, timeout=30,
                            )
                            if result.returncode == 0:
                                started = True
                            break

                # Wait for service to be ready (up to 10s)
                for _ in range(10):
                    time.sleep(1)
                    if self._is_port_open('localhost', POSTGRES_PORT):
                        return self._verify_postgres_connection()
                return False

            elif self.platform_name == 'Windows':
                # Try net start first (works if installed as service)
                for svc_name in ['postgresql-x64-17', 'postgresql-x64-16', 'postgresql-x64-15', 'postgresql']:
                    result = subprocess.run(
                        ['net', 'start', svc_name],
                        capture_output=True, timeout=30,
                    )
                    if result.returncode == 0:
                        break
                else:
                    # Fallback: try pg_ctl directly
                    pg_base = Path('C:/Program Files/PostgreSQL')
                    if pg_base.exists():
                        for pg_dir in sorted(pg_base.iterdir(), reverse=True):
                            pg_ctl = pg_dir / 'bin' / 'pg_ctl.exe'
                            data_dir = pg_dir / 'data'
                            if pg_ctl.exists() and data_dir.exists():
                                subprocess.run(
                                    [str(pg_ctl), 'start', '-D', str(data_dir), '-w'],
                                    capture_output=True, timeout=30,
                                )
                                break
                time.sleep(3)
                return self._verify_postgres_connection()
            else:
                return False
        except Exception as e:
            print(f"{self._colorize(f'Warning: {e}', Color.YELLOW)}")
            return False

    def _verify_postgres_connection(self) -> bool:
        """Verify PostgreSQL accepts queries, not just that the port is open.

        Falls back to the port-open check if psql is unavailable.
        """
        try:
            result = subprocess.run(
                ['psql', '-h', 'localhost', '-p', str(POSTGRES_PORT),
                 '-U', 'postgres', '-c', 'SELECT 1', '--no-password'],
                capture_output=True, text=True, timeout=5,
                env={**os.environ, 'PGCONNECT_TIMEOUT': '3'},
            )
            if result.returncode == 0:
                return True
            # psql failed — fall through to port check with a warning
            print(self._colorize(
                '  Note: psql query check failed, falling back to port check.',
                Color.GRAY,
            ))
        except FileNotFoundError:
            # psql not on PATH — fall back silently
            pass
        except (subprocess.TimeoutExpired, Exception):
            print(self._colorize(
                '  Note: psql verification timed out, falling back to port check.',
                Color.GRAY,
            ))
        return self._is_port_open('localhost', POSTGRES_PORT)

    def _start_redis(self) -> bool:
        """Attempt to start Redis service."""
        try:
            if self.platform_name == 'Darwin':  # macOS
                result = subprocess.run(
                    ['brew', 'services', 'start', 'redis'],
                    capture_output=True,
                    timeout=30
                )
                if result.returncode != 0:
                    # Fallback: start redis-server directly in background
                    subprocess.Popen(
                        ['redis-server', '--daemonize', 'yes'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                time.sleep(2)
                return self._is_port_open('localhost', REDIS_PORT)

            elif self.platform_name == 'Linux':
                # Try both service names: Debian/Ubuntu uses 'redis-server',
                # Fedora/Arch use 'redis'
                for svc_name in ['redis-server', 'redis']:
                    result = subprocess.run(
                        [*_sudo(), 'systemctl', 'start', svc_name],
                        capture_output=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        break
                else:
                    # Fallback: start redis-server directly
                    subprocess.Popen(
                        ['redis-server', '--daemonize', 'yes'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                time.sleep(2)
                return self._is_port_open('localhost', REDIS_PORT)

            elif self.platform_name == 'Windows':
                # Try net start for both Redis and Memurai
                for svc_name in ['Redis', 'redis', 'Memurai']:
                    result = subprocess.run(
                        ['net', 'start', svc_name],
                        capture_output=True, timeout=30,
                    )
                    if result.returncode == 0:
                        break
                else:
                    # Fallback: start redis-server directly
                    if shutil.which('redis-server'):
                        subprocess.Popen(
                            ['redis-server'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                    elif shutil.which('memurai'):
                        subprocess.Popen(
                            ['memurai'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                time.sleep(2)
                return self._is_port_open('localhost', REDIS_PORT)
            else:
                return False
        except Exception as e:
            print(f"{self._colorize(f'Warning: {e}', Color.YELLOW)}")
            return False

    # Swap file path used during low-memory pip installs (Linux only)
    _SWAP_PATH = '/swapfile_dyslex'

    def _create_backend_venv(self) -> bool:
        """Create backend virtual environment and install dependencies."""
        try:
            backend_dir = Path('backend').resolve()

            # Ensure the venv module is available
            check = subprocess.run(
                [sys.executable, '-m', 'venv', '--help'],
                capture_output=True, timeout=10,
            )
            if check.returncode != 0:
                plat = platform.system()
                if plat == 'Linux' and self.installer:
                    pkg = self.installer._detect_package_manager()
                    if pkg == 'apt':
                        if self.installer._dpkg_broken:
                            print(f"{self._colorize('  Skipping apt (dpkg is broken — see above)', Color.YELLOW)}")
                        else:
                            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
                            print(f"{self._colorize('  Installing python3-venv (required on Ubuntu)...', Color.GRAY)}")
                            subprocess.run(
                                [*_sudo(), 'apt-get', 'install', '-y', '-qq',
                                 f'python{py_ver}-venv', 'python3-venv'],
                                timeout=120,
                            )
                    elif pkg == 'dnf':
                        print(f"{self._colorize('  Installing python3-venv...', Color.GRAY)}")
                        subprocess.run(
                            [*_sudo(), 'dnf', 'install', '-y', '-q', 'python3-libs'],
                            timeout=120,
                        )
                elif plat == 'Darwin':
                    # macOS: try reinstalling python via brew to get venv module
                    print(f"{self._colorize('  Python venv module missing, reinstalling Python...', Color.GRAY)}")
                    subprocess.run(
                        ['brew', 'install', 'python3'],
                        capture_output=True, timeout=300,
                    )
                elif plat == 'Windows':
                    # Windows: python.org installer includes venv; try pip as fallback
                    print(f"{self._colorize('  Python venv module missing, trying virtualenv fallback...', Color.GRAY)}")
                    subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', 'virtualenv'],
                        capture_output=True, timeout=120,
                    )

            # Create venv — try venv first, fall back to virtualenv on Windows
            venv_path = backend_dir / 'venv'
            print(f"{self._colorize('  Creating virtual environment...', Color.GRAY)}")
            result = subprocess.run(
                [sys.executable, '-m', 'venv', 'venv'],
                cwd=str(backend_dir),
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                if platform.system() == 'Windows':
                    # Fallback: try virtualenv
                    result = subprocess.run(
                        [sys.executable, '-m', 'virtualenv', 'venv'],
                        cwd=str(backend_dir),
                        capture_output=True,
                        timeout=60,
                    )
                if result.returncode != 0:
                    print(f"{self._colorize(f'  Error: {result.stderr.decode()}', Color.RED)}")
                    return False

            # Track created venv for rollback on later failure
            self.created_artifacts.append(('venv', venv_path))

            # Wait for venv to be fully created
            time.sleep(1)

            # Verify the venv python binary works (catches broken symlinks)
            venv_python_check = venv_path / 'bin' / 'python'
            if not venv_python_check.exists():
                venv_python_check = venv_path / 'Scripts' / 'python.exe'
            if venv_python_check.exists():
                try:
                    check_result = subprocess.run(
                        [str(venv_python_check), '-c', 'import sys; print(sys.executable)'],
                        capture_output=True, text=True, timeout=10,
                    )
                    if check_result.returncode != 0:
                        print(f"{self._colorize('  Venv python is broken, recreating...', Color.YELLOW)}")
                        shutil.rmtree(venv_path)
                        result = subprocess.run(
                            [sys.executable, '-m', 'venv', 'venv'],
                            cwd=str(backend_dir),
                            capture_output=True, timeout=60,
                        )
                        if result.returncode != 0:
                            print(f"{self._colorize(f'  Error: {result.stderr.decode()}', Color.RED)}")
                            return False
                        time.sleep(1)
                except Exception:
                    pass  # Best-effort check; proceed if it can't run
            else:
                print(f"{self._colorize('  Venv python binary not found after creation, recreating...', Color.YELLOW)}")
                shutil.rmtree(venv_path)
                result = subprocess.run(
                    [sys.executable, '-m', 'venv', 'venv'],
                    cwd=str(backend_dir),
                    capture_output=True, timeout=60,
                )
                if result.returncode != 0:
                    print(f"{self._colorize(f'  Error: {result.stderr.decode()}', Color.RED)}")
                    return False
                time.sleep(1)

            # Find pip in the new venv — check multiple possible locations
            venv_pip = None
            pip_candidates = [
                backend_dir / 'venv' / 'bin' / 'pip',
                backend_dir / 'venv' / 'bin' / 'pip3',
                backend_dir / 'venv' / 'Scripts' / 'pip.exe',
                backend_dir / 'venv' / 'Scripts' / 'pip3.exe',
            ]
            for candidate in pip_candidates:
                if candidate.exists():
                    venv_pip = candidate
                    break

            if not venv_pip:
                # Last resort: try to bootstrap pip via ensurepip
                print(f"{self._colorize('  pip not found in venv, bootstrapping...', Color.GRAY)}")
                venv_python = backend_dir / 'venv' / 'bin' / 'python'
                if not venv_python.exists():
                    venv_python = backend_dir / 'venv' / 'Scripts' / 'python.exe'
                if venv_python.exists():
                    subprocess.run(
                        [str(venv_python), '-m', 'ensurepip', '--upgrade'],
                        cwd=str(backend_dir),
                        capture_output=True, timeout=60,
                    )
                    # Re-check for pip
                    for candidate in pip_candidates:
                        if candidate.exists():
                            venv_pip = candidate
                            break

            if not venv_pip:
                print(f"{self._colorize('  Error: pip not found in venv', Color.RED)}")
                return False

            # Upgrade pip first to avoid build failures with older versions
            subprocess.run(
                [str(venv_pip), 'install', '--upgrade', 'pip', 'setuptools', 'wheel'],
                cwd=str(backend_dir),
                capture_output=True,
                timeout=120,
            )

            # On macOS, ensure brew library paths are available for C extension builds
            if platform.system() == 'Darwin':
                for lib in ['openssl', 'libpq', 'libffi']:
                    prefix = subprocess.run(
                        ['brew', '--prefix', lib],
                        capture_output=True, text=True, timeout=10,
                    )
                    if prefix.returncode == 0 and prefix.stdout.strip():
                        lib_path = prefix.stdout.strip()
                        os.environ['LDFLAGS'] = os.environ.get('LDFLAGS', '') + f' -L{lib_path}/lib'
                        os.environ['CPPFLAGS'] = os.environ.get('CPPFLAGS', '') + f' -I{lib_path}/include'

            # Install dependencies in batches to avoid OOM on low-memory VMs.
            print(f"{self._colorize('  Installing dependencies in batches (this may take a while)...', Color.GRAY)}")

            # --- Detect available memory and create swap if needed ---
            low_memory = False
            created_swap = False
            swap_path = self._SWAP_PATH

            # Failsafe: clean up stale swap files from a previous crashed run
            if platform.system() == 'Linux' and os.path.exists(swap_path):
                print(f"{self._colorize('  Cleaning up stale swap file from previous run...', Color.GRAY)}")
                try:
                    subprocess.run([*_sudo(), 'swapoff', swap_path],
                                   capture_output=True, timeout=30)
                except Exception:
                    pass
                try:
                    subprocess.run([*_sudo(), 'rm', '-f', swap_path],
                                   capture_output=True, timeout=10)
                except Exception:
                    pass

            # Atexit handler for signal-safe swap cleanup
            def _atexit_swap_cleanup():
                """Emergency swap cleanup registered via atexit."""
                if os.path.exists(swap_path):
                    try:
                        subprocess.run([*_sudo(), 'swapoff', swap_path],
                                       capture_output=True, timeout=30)
                    except Exception:
                        pass
                    try:
                        subprocess.run([*_sudo(), 'rm', '-f', swap_path],
                                       capture_output=True, timeout=10)
                    except Exception:
                        pass

            try:
                if platform.system() == 'Linux':
                    with open('/proc/meminfo') as f:
                        for line in f:
                            if line.startswith('MemTotal:'):
                                mem_kb = int(line.split()[1])
                                mem_gb = mem_kb / 1024 / 1024
                                if mem_gb < 4:
                                    low_memory = True
                                    print(f"{self._colorize(f'  Low memory detected ({mem_gb:.1f}GB). Creating swap file...', Color.YELLOW)}")
                                    # Register atexit handler BEFORE creating swap
                                    atexit.register(_atexit_swap_cleanup)
                                    # Create a 4GB swap file
                                    swap_cmds = [
                                        [*_sudo(), 'fallocate', '-l', '4G', swap_path],
                                        [*_sudo(), 'chmod', '600', swap_path],
                                        [*_sudo(), 'mkswap', swap_path],
                                        [*_sudo(), 'swapon', swap_path],
                                    ]
                                    for cmd in swap_cmds:
                                        r = subprocess.run(cmd, capture_output=True, timeout=60)
                                        if r.returncode != 0:
                                            # fallocate may not work on all filesystems, try dd
                                            if 'fallocate' in cmd:
                                                dd_result = subprocess.run(
                                                    [*_sudo(), 'dd', 'if=/dev/zero', f'of={swap_path}',
                                                     'bs=1M', 'count=4096'],
                                                    capture_output=True, timeout=120,
                                                )
                                                if dd_result.returncode != 0:
                                                    break
                                            else:
                                                break
                                    else:
                                        created_swap = True
                                        print(f"{self._colorize('  ✓ 4GB swap file created', Color.GREEN)}")
                                break
                elif platform.system() == 'Darwin':
                    # macOS: check with sysctl
                    result = subprocess.run(
                        ['sysctl', '-n', 'hw.memsize'],
                        capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0:
                        mem_bytes = int(result.stdout.strip())
                        if mem_bytes < 4 * 1024 * 1024 * 1024:
                            low_memory = True
            except Exception:
                pass  # Can't detect memory — proceed normally

            # Parse requirements.txt into ordered batches — heavy packages last
            requirements_file = backend_dir / 'requirements.txt'
            heavy_packages = {'torch', 'transformers', 'datasets', 'accelerate',
                              'onnx', 'onnxruntime', 'optimum', 'peft', 'numpy'}
            light_reqs = []
            heavy_reqs = []
            with open(requirements_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    pkg_name = line.split('>=')[0].split('<=')[0].split('==')[0].split('[')[0].strip()
                    if pkg_name.lower() in heavy_packages:
                        heavy_reqs.append(line)
                    else:
                        light_reqs.append(line)

            pip_base = [str(venv_pip), 'install', '--no-cache-dir']

            # Helper: retry pip installs via the installer if available
            def _pip_retry(cmd, desc, timeout=600):
                if self.installer:
                    return self.installer._retry_command(
                        cmd, description=desc, timeout=timeout,
                        cwd=str(backend_dir),
                    )
                return subprocess.run(
                    cmd, cwd=str(backend_dir),
                    capture_output=False, timeout=timeout,
                )

            # Batch 1: lightweight packages (framework, db, auth, utils, dev)
            if light_reqs:
                print(f"{self._colorize(f'  [1/3] Installing core packages ({len(light_reqs)})...', Color.GRAY)}")
                result = _pip_retry(pip_base + light_reqs, 'pip install (core)', timeout=600)
                if result.returncode != 0:
                    print(f"{self._colorize('  Core package install failed', Color.RED)}")
                    return False

            # Batch 2: ML packages one at a time
            # Install order matters — torch first (others depend on it),
            # numpy before datasets/transformers.
            install_order = ['numpy', 'torch', 'onnx', 'onnxruntime',
                             'accelerate', 'peft', 'transformers', 'datasets', 'optimum']
            ordered_heavy = []
            heavy_map = {}
            for req in heavy_reqs:
                pkg_name = req.split('>=')[0].split('<=')[0].split('==')[0].split('[')[0].strip().lower()
                heavy_map[pkg_name] = req
            for name in install_order:
                if name in heavy_map:
                    ordered_heavy.append(heavy_map.pop(name))
            # Append any remaining that weren't in the explicit order
            ordered_heavy.extend(heavy_map.values())

            for i, req in enumerate(ordered_heavy, 1):
                pkg_display = req.split('>=')[0].split('[')[0].strip()
                print(f"{self._colorize(f'  [2/3] Installing ML package {i}/{len(ordered_heavy)}: {pkg_display}...', Color.GRAY)}")

                install_cmd = pip_base.copy()

                # For torch: use CPU-only build (much smaller, won't OOM)
                if pkg_display.lower() == 'torch':
                    install_cmd += ['--index-url', 'https://download.pytorch.org/whl/cpu']

                install_cmd.append(req)

                result = _pip_retry(install_cmd, f'pip install {pkg_display}', timeout=900)
                if result.returncode != 0:
                    print(f"{self._colorize(f'  Warning: {pkg_display} failed to install (ML features may be limited)', Color.YELLOW)}")

            # Batch 3: verify critical imports work
            print(f"{self._colorize('  [3/3] Verifying installation...', Color.GRAY)}")
            venv_python = backend_dir / 'venv' / 'bin' / 'python'
            if not venv_python.exists():
                venv_python = backend_dir / 'venv' / 'Scripts' / 'python.exe'
            if venv_python.exists():
                check = subprocess.run(
                    [str(venv_python), '-c', 'import fastapi; import sqlalchemy; print("OK")'],
                    cwd=str(backend_dir),
                    capture_output=True, text=True, timeout=30,
                )
                if check.returncode != 0:
                    print(f"{self._colorize('  Warning: core imports failed — dependencies may be incomplete', Color.YELLOW)}")
                    return False

            # Clean up swap file if we created one
            if created_swap:
                try:
                    subprocess.run([*_sudo(), 'swapoff', swap_path],
                                   capture_output=True, timeout=30)
                    subprocess.run([*_sudo(), 'rm', '-f', swap_path],
                                   capture_output=True, timeout=10)
                    print(f"{self._colorize('  ✓ Temporary swap file removed', Color.GREEN)}")
                except Exception:
                    pass
                # Unregister atexit handler — normal cleanup succeeded
                atexit.unregister(_atexit_swap_cleanup)

            return True
        except Exception as e:
            print(f"{self._colorize(f'Error creating venv: {e}', Color.YELLOW)}")
            import traceback
            traceback.print_exc()
            # Clean up swap file on exception
            if os.path.exists(self._SWAP_PATH):
                try:
                    subprocess.run([*_sudo(), 'swapoff', self._SWAP_PATH],
                                   capture_output=True, timeout=30)
                    subprocess.run([*_sudo(), 'rm', '-f', self._SWAP_PATH],
                                   capture_output=True, timeout=10)
                    print(f"{self._colorize('  ✓ Temporary swap file removed after error', Color.GREEN)}")
                except Exception:
                    pass
            # Remove partial venv to prevent "already exists" false positives
            partial_venv = Path('backend').resolve() / 'venv'
            if partial_venv.exists():
                print(f"{self._colorize('  Removing partial venv...', Color.GRAY)}")
                try:
                    shutil.rmtree(partial_venv)
                except Exception:
                    pass
            return False

    def _kill_port_process(self, port: int) -> bool:
        """Kill the process using the specified port."""
        try:
            if self.platform_name == 'Darwin' or self.platform_name == 'Linux':
                pids = _find_pids_on_port(port)
                if pids:
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except (ProcessLookupError, PermissionError, ValueError):
                            pass
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
                for svc_name in ['postgresql@17', 'postgresql@16', 'postgresql@15', 'postgresql']:
                    result = subprocess.run(
                        ['brew', 'services', 'stop', svc_name],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        break
                print(f"{self._colorize('✓ PostgreSQL stopped', Color.GREEN)}")
            elif self.platform_name == 'Linux':
                subprocess.run(
                    [*_sudo(), 'systemctl', 'stop', 'postgresql'],
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
                for svc_name in ['redis-server', 'redis']:
                    result = subprocess.run(
                        [*_sudo(), 'systemctl', 'stop', svc_name],
                        capture_output=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        break
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
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._sync_http_check, url)
            return bool(result)
        except Exception:
            return False

    def _sync_http_check(self, url: str):
        """Synchronous HTTP check helper.

        For /health/ready endpoint, accepts both "ready" (200) and "degraded" (503)
        status responses. A degraded response means the backend is running but Redis
        or DB may not be fully connected yet — acceptable for startup.
        """
        timeout = HEALTH_CHECK_REQUEST_TIMEOUT
        try:
            if url.startswith("https://"):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urlopen(url, timeout=timeout, context=ctx) as response:
                    body = response.read().decode('utf-8', errors='replace')
                    data = json.loads(body)
                    return data.get('status') in ('ready', 'degraded')
            else:
                with urlopen(url, timeout=timeout) as response:
                    body = response.read().decode('utf-8', errors='replace')
                    data = json.loads(body)
                    return data.get('status') in ('ready', 'degraded')
        except HTTPError as e:
            # /health/ready returns 503 for "degraded" — still means backend is alive
            if e.code == 503:
                try:
                    body = e.read().decode('utf-8', errors='replace')
                    data = json.loads(body)
                    return data.get('status') == 'degraded'
                except Exception:
                    pass
            raise


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
        self._managed_ports: List[int] = []  # Ports we started services on

    async def start_all(self):
        """Start all services based on configuration."""
        mode = self.config['mode']

        # Collect managed ports and kill any stale processes on them
        if mode in ['dev', 'backend']:
            self._managed_ports.append(self.config.get('backend_port', DEFAULT_BACKEND_PORT))
        if mode in ['dev', 'frontend']:
            self._managed_ports.append(self.config.get('frontend_port', DEFAULT_FRONTEND_PORT))
        self._kill_stale_port_processes()

        if mode == 'docker':
            await self.start_docker()
            await self._wait_for_health()
        else:
            if mode in ['dev', 'backend']:
                await self.start_backend()
                # Wait for backend to be healthy before starting frontend
                await self._wait_for_backend_health()

            if mode in ['dev', 'frontend']:
                await self.start_frontend()

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
            cwd=str(Path('backend')),
            start_new_session=True
        )

        self.processes['backend'] = process

        # Start log streaming tasks
        stdout = process.stdout
        stderr = process.stderr
        if stdout:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stdout, 'backend', 'stdout'))
            )
        if stderr:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stderr, 'backend', 'stderr'))
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
            env=env,
            start_new_session=True
        )

        self.processes['frontend'] = process

        # Start log streaming tasks
        stdout = process.stdout
        stderr = process.stderr
        if stdout:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stdout, 'frontend', 'stdout'))
            )
        if stderr:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stderr, 'frontend', 'stderr'))
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
        stdout = process.stdout
        stderr = process.stderr
        if stdout:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stdout, 'docker', 'stdout'))
            )
        if stderr:
            self.stream_tasks.append(
                asyncio.create_task(self.logger.read_stream(stderr, 'docker', 'stderr'))
            )

    async def _wait_for_backend_health(self):
        """Wait for the backend to become healthy before proceeding."""
        protocol = "https" if self.config.get('https') else "http"
        port = self.config.get('backend_port', DEFAULT_BACKEND_PORT)
        url = BACKEND_HEALTH_ENDPOINT.format(protocol=protocol, port=port)
        success = await self.health_monitor.wait_for_service(
            'Backend',
            url,
            BACKEND_STARTUP_TIMEOUT
        )
        if not success:
            raise RuntimeError("Backend failed to start")

    async def _wait_for_health(self):
        """Wait for Docker services to become healthy."""
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

        # Stop each process (kills entire process group)
        for service, process in self.processes.items():
            await self._stop_process(service, process)

        # Final cleanup: kill anything still on our managed ports
        self._kill_stale_port_processes()

        await self.logger.success('system', "Shutdown complete")

    async def _stop_process(self, service: str, process: asyncio.subprocess.Process):
        """Stop a process and its entire process group."""
        if process.returncode is not None:
            # Already stopped
            return

        await self.logger.info(service, "Stopping...")

        try:
            # Kill the entire process group (catches all children)
            try:
                if platform.system() != 'Windows':
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
            except (ProcessLookupError, PermissionError, OSError):
                process.terminate()

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=SHUTDOWN_TIMEOUT)
                await self.logger.success(service, "Stopped")
            except asyncio.TimeoutError:
                # Force kill the entire process group
                await self.logger.warning(service, "Force killing...")
                try:
                    if platform.system() != 'Windows':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except (ProcessLookupError, PermissionError, OSError):
                    process.kill()
                await process.wait()
                await self.logger.success(service, "Killed")
        except ProcessLookupError:
            # Already dead
            pass

    def _kill_stale_port_processes(self):
        """Kill any stale processes on managed ports."""
        if not self._managed_ports:
            return
        for port in self._managed_ports:
            try:
                if platform.system() in ('Darwin', 'Linux'):
                    pids = set(_find_pids_on_port(port))
                    if pids:
                        # Don't kill our own children (they're managed via process groups)
                        own_pids = {str(p.pid) for p in self.processes.values()
                                    if p.returncode is None}
                        stale_pids = pids - own_pids - {str(os.getpid())}
                        for pid in stale_pids:
                            try:
                                os.kill(int(pid), signal.SIGTERM)
                            except (ProcessLookupError, PermissionError, ValueError):
                                pass
                        if stale_pids:
                            time.sleep(1)
                            # Force kill any survivors
                            for pid in stale_pids:
                                try:
                                    os.kill(int(pid), signal.SIGKILL)
                                except (ProcessLookupError, PermissionError, ValueError):
                                    pass
                elif platform.system() == 'Windows':
                    result = subprocess.run(
                        f'netstat -ano | findstr :{port}',
                        capture_output=True, text=True,
                        shell=True, timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split()
                            if len(parts) > 4:
                                try:
                                    subprocess.run(
                                        ['taskkill', '/F', '/PID', parts[-1]],
                                        timeout=5
                                    )
                                except Exception:
                                    pass
            except Exception:
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
  python run.py --auto-setup       # Install everything + start (one command!)
  python run.py --auto-setup -y    # Same, skip confirmation prompts
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
        help='Automatically install missing prerequisites, start services, and create venv'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompts for package installations (use with --auto-setup)'
    )
    parser.add_argument(
        '--kill-ports',
        action='store_true',
        help='Automatically kill processes using required ports'
    )
    parser.add_argument(
        '--startup-timeout',
        type=int,
        default=None,
        help='Backend startup timeout in seconds (default: 30, overrides DYSLEX_BACKEND_TIMEOUT env var)'
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

    # Acquire process lock — prevent concurrent instances
    lock = ProcessLock(script_dir / '.dyslex.lock')
    if not lock.acquire():
        sys.exit(1)
    atexit.register(lock.release)

    # Load environment variables from .env if present
    load_dotenv()

    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Smart first-run detection: validate venv integrity, not just existence
    if not args.auto_setup:
        trigger, reason = should_auto_setup(script_dir)
        if trigger:
            print(f"\n{Color.CYAN}{Color.BOLD}{reason}{Color.RESET}")
            print(f"  Enabling --auto-setup to install prerequisites automatically.\n")
            args.auto_setup = True

    # Determine mode
    if args.docker:
        mode = 'docker'
    elif args.backend_only:
        mode = 'backend'
    elif args.frontend_only:
        mode = 'frontend'
    else:
        mode = 'dev'

    # Apply configurable startup timeouts from env vars or CLI flag
    global BACKEND_STARTUP_TIMEOUT, FRONTEND_STARTUP_TIMEOUT
    if args.startup_timeout is not None:
        BACKEND_STARTUP_TIMEOUT = args.startup_timeout
    elif os.getenv('DYSLEX_BACKEND_TIMEOUT'):
        try:
            BACKEND_STARTUP_TIMEOUT = int(os.environ['DYSLEX_BACKEND_TIMEOUT'])
        except ValueError:
            pass
    if os.getenv('DYSLEX_FRONTEND_TIMEOUT'):
        try:
            FRONTEND_STARTUP_TIMEOUT = int(os.environ['DYSLEX_FRONTEND_TIMEOUT'])
        except ValueError:
            pass

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
        'yes': args.yes,
        'kill_ports': args.kill_ports,
        'check_only': args.check_only,
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
            lock.release()
            sys.exit(1)

        if args.check_only:
            lock.release()
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

        # Release the process lock
        lock.release()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        sys.exit(0)
