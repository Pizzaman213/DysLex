"""Shared fixtures for cross-platform installation tests.

Provides mocks for platform detection, subprocess calls, and factory
fixtures for PackageInstaller / PrerequisiteChecker instances.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run import PackageInstaller, PrerequisiteChecker, CheckError, CheckWarning, CheckSkipped


# ---------------------------------------------------------------------------
# PackageInstaller factory
# ---------------------------------------------------------------------------

@pytest.fixture
def installer():
    """Fresh PackageInstaller with color disabled and --yes mode."""
    return PackageInstaller(color_enabled=False, yes=True)


# ---------------------------------------------------------------------------
# Platform mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_macos():
    """Patch platform.system() to return 'Darwin'."""
    with patch("run.platform.system", return_value="Darwin"):
        yield


@pytest.fixture
def mock_linux():
    """Patch platform.system() to return 'Linux'."""
    with patch("run.platform.system", return_value="Linux"):
        yield


@pytest.fixture
def mock_windows():
    """Patch platform.system() to return 'Windows'."""
    with patch("run.platform.system", return_value="Windows"):
        yield


def _make_os_release(distro_id: str, id_like: str = "") -> str:
    """Build a minimal /etc/os-release string."""
    lines = [f'ID={distro_id}']
    if id_like:
        lines.append(f'ID_LIKE={id_like}')
    return "\n".join(lines) + "\n"


@pytest.fixture
def mock_ubuntu(mock_linux):
    """Linux + /etc/os-release ID=ubuntu."""
    content = _make_os_release("ubuntu", "debian")
    with patch("run.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)):
        yield


@pytest.fixture
def mock_fedora(mock_linux):
    """Linux + /etc/os-release ID=fedora."""
    content = _make_os_release("fedora")
    with patch("run.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)):
        yield


@pytest.fixture
def mock_arch(mock_linux):
    """Linux + /etc/os-release ID=arch."""
    content = _make_os_release("arch")
    with patch("run.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)):
        yield


@pytest.fixture
def mock_os_release():
    """Factory fixture: mock /etc/os-release with arbitrary content.

    Usage:
        def test_something(mock_os_release):
            mock_os_release("pop", id_like="ubuntu debian")
    """
    def _factory(distro_id: str, id_like: str = ""):
        content = _make_os_release(distro_id, id_like)
        return (
            patch("run.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=content)),
        )
    return _factory


# ---------------------------------------------------------------------------
# Subprocess mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_subprocess():
    """Patch subprocess.run globally with a configurable MagicMock.

    The mock returns returncode=0 and empty stdout/stderr by default.
    Tests can override via mock_subprocess.return_value or side_effect.
    """
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("run.subprocess.run", return_value=mock_result) as mock_run:
        mock_run._default_result = mock_result
        yield mock_run


# ---------------------------------------------------------------------------
# PrerequisiteChecker factory
# ---------------------------------------------------------------------------

@pytest.fixture
def checker_factory():
    """Factory that creates PrerequisiteChecker with configurable options.

    Usage:
        checker = checker_factory(mode="dev", auto_setup=True)
    """
    def _factory(
        mode: str = "dev",
        auto_setup: bool = False,
        yes: bool = True,
        backend_port: int = 8000,
        frontend_port: int = 3000,
        kill_ports: bool = False,
    ):
        config = {
            "auto_setup": auto_setup,
            "yes": yes,
            "backend_port": backend_port,
            "frontend_port": frontend_port,
            "kill_ports": kill_ports,
        }
        return PrerequisiteChecker(
            mode=mode,
            config=config,
            color_enabled=False,
        )
    return _factory
