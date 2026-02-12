"""Tests for PackageInstaller install methods.

All subprocess calls are mocked — no real installations occur.
"""

import subprocess
import pytest
from unittest.mock import patch, MagicMock, call

from run import PackageInstaller


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Create a mock subprocess.CompletedProcess."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _fresh_installer(platform_name: str = "Darwin") -> PackageInstaller:
    """Create a fresh installer with the given platform."""
    inst = PackageInstaller(color_enabled=False, yes=True)
    inst.platform_name = platform_name
    return inst


# ============================================================================
# TestIsCommandAvailable
# ============================================================================

class TestIsCommandAvailable:

    def test_unix_uses_which(self):
        inst = _fresh_installer("Darwin")
        with patch("run.subprocess.run", return_value=_make_result(0)) as mock_run:
            assert inst._is_command_available("node") is True
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["which", "node"]

    def test_windows_uses_where(self):
        inst = _fresh_installer("Windows")
        with patch("run.subprocess.run", return_value=_make_result(0)) as mock_run:
            assert inst._is_command_available("node") is True
            assert mock_run.call_args[0][0] == ["where", "node"]

    def test_command_not_found_returns_false(self):
        inst = _fresh_installer("Darwin")
        with patch("run.subprocess.run", return_value=_make_result(1)):
            assert inst._is_command_available("nonexistent") is False

    def test_exception_returns_false(self):
        inst = _fresh_installer("Darwin")
        with patch("run.subprocess.run", side_effect=FileNotFoundError):
            assert inst._is_command_available("node") is False


# ============================================================================
# TestEnsureHomebrew
# ============================================================================

class TestEnsureHomebrew:

    @pytest.mark.platform_macos
    def test_returns_true_if_already_available(self):
        inst = _fresh_installer("Darwin")
        with patch.object(inst, "_is_command_available", return_value=True):
            assert inst._ensure_homebrew() is True

    @pytest.mark.platform_macos
    def test_installs_if_missing_and_user_confirms(self):
        inst = _fresh_installer("Darwin")
        with patch.object(inst, "_is_command_available", return_value=False), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.Path.exists", return_value=False):
            assert inst._ensure_homebrew() is True

    @pytest.mark.platform_macos
    def test_returns_false_if_user_declines(self):
        inst = PackageInstaller(color_enabled=False, yes=False)
        inst.platform_name = "Darwin"
        with patch.object(inst, "_is_command_available", return_value=False), \
             patch("builtins.input", return_value="n"):
            assert inst._ensure_homebrew() is False


# ============================================================================
# TestEnsureChocolatey
# ============================================================================

class TestEnsureChocolatey:

    @pytest.mark.platform_windows
    def test_returns_true_if_already_available(self):
        inst = _fresh_installer("Windows")
        with patch.object(inst, "_is_command_available", return_value=True):
            assert inst._ensure_chocolatey() is True

    @pytest.mark.platform_windows
    def test_installs_if_missing_and_user_confirms(self):
        inst = _fresh_installer("Windows")
        with patch.object(inst, "_is_command_available", return_value=False), \
             patch("run.subprocess.run", return_value=_make_result(0)):
            assert inst._ensure_chocolatey() is True

    @pytest.mark.platform_windows
    def test_returns_false_if_user_declines(self):
        inst = PackageInstaller(color_enabled=False, yes=False)
        inst.platform_name = "Windows"
        with patch.object(inst, "_is_command_available", return_value=False), \
             patch("builtins.input", return_value="n"):
            assert inst._ensure_chocolatey() is False


# ============================================================================
# TestInstallNode
# ============================================================================

class TestInstallNode:

    @pytest.mark.platform_macos
    def test_macos_installs_via_brew(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_node() is True

    @pytest.mark.platform_linux
    def test_ubuntu_installs_via_apt_nodesource(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "apt"

        def side_effect(cmd, **kwargs):
            return _make_result(0)

        with patch("run.subprocess.run", side_effect=side_effect), \
             patch.object(inst, "_is_command_available", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_node() is True

    @pytest.mark.platform_linux
    def test_ubuntu_fallback_when_nodesource_fails(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "apt"

        call_count = [0]
        def side_effect(cmd, **kwargs):
            call_count[0] += 1
            # NodeSource curl command fails
            if isinstance(cmd, list) and "bash" in cmd[0] and any("nodesource" in str(c) for c in cmd):
                return _make_result(1)
            return _make_result(0)

        with patch("run.subprocess.run", side_effect=side_effect), \
             patch.object(inst, "_is_command_available", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_node() is True

    @pytest.mark.platform_linux
    def test_fedora_installs_via_dnf(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "dnf"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_node() is True

    @pytest.mark.platform_linux
    def test_arch_installs_via_pacman(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "pacman"
        with patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_node() is True

    @pytest.mark.platform_windows
    def test_windows_installs_via_choco(self):
        inst = _fresh_installer("Windows")
        inst._pkg_manager = "choco"
        with patch.object(inst, "_ensure_chocolatey", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_node() is True

    def test_no_package_manager_returns_false(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = None
        with patch.object(inst, "_detect_package_manager", return_value=None):
            assert inst.install_node() is False

    def test_user_declines_returns_false(self):
        inst = PackageInstaller(color_enabled=False, yes=False)
        inst.platform_name = "Darwin"
        with patch("builtins.input", return_value="n"):
            assert inst.install_node() is False

    @pytest.mark.platform_macos
    def test_node_not_available_after_install_returns_false(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"

        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=False), \
             patch("run.Path.glob", return_value=iter([])):
            assert inst.install_node() is False

    @pytest.mark.platform_macos
    def test_exception_returns_false(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", side_effect=subprocess.TimeoutExpired("brew", 600)):
            assert inst.install_node() is False


# ============================================================================
# TestInstallPostgres
# ============================================================================

class TestInstallPostgres:

    @pytest.mark.platform_macos
    def test_macos_installs_via_brew(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.Path.glob", return_value=iter([])):
            assert inst.install_postgres() is True

    @pytest.mark.platform_linux
    def test_ubuntu_installs_via_apt(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "apt"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_postgres() is True

    @pytest.mark.platform_linux
    def test_fedora_installs_via_dnf_with_initdb(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "dnf"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_postgres() is True

    @pytest.mark.platform_linux
    def test_arch_installs_via_pacman_with_initdb(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "pacman"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_postgres() is True

    @pytest.mark.platform_windows
    def test_windows_installs_via_choco(self):
        inst = _fresh_installer("Windows")
        inst._pkg_manager = "choco"
        with patch.object(inst, "_ensure_chocolatey", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_postgres() is True

    def test_exception_returns_false(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", side_effect=OSError("disk full")):
            assert inst.install_postgres() is False


# ============================================================================
# TestInstallRedis
# ============================================================================

class TestInstallRedis:

    @pytest.mark.platform_macos
    def test_macos_installs_via_brew(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_redis() is True

    @pytest.mark.platform_linux
    def test_ubuntu_installs_via_apt(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "apt"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_redis() is True

    @pytest.mark.platform_linux
    def test_fedora_installs_via_dnf(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "dnf"
        with patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_redis() is True

    @pytest.mark.platform_linux
    def test_arch_installs_via_pacman(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "pacman"
        with patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_redis() is True

    @pytest.mark.platform_windows
    def test_windows_tries_redis64_then_memurai(self):
        inst = _fresh_installer("Windows")
        inst._pkg_manager = "choco"

        call_count = [0]
        def side_effect(cmd, **kwargs):
            call_count[0] += 1
            # redis-64 fails, memurai succeeds
            if isinstance(cmd, list) and "redis-64" in cmd:
                return _make_result(1)
            return _make_result(0)

        with patch.object(inst, "_ensure_chocolatey", return_value=True), \
             patch("run.subprocess.run", side_effect=side_effect), \
             patch.object(inst, "_is_command_available", return_value=True):
            assert inst.install_redis() is True

    def test_redis_not_available_after_install_returns_false(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch.object(inst, "_run_command", return_value=_make_result(0)), \
             patch.object(inst, "_is_command_available", return_value=False):
            assert inst.install_redis() is False


# ============================================================================
# TestInstallSystemPrerequisites
# ============================================================================

class TestInstallSystemPrerequisites:

    def test_skips_when_no_package_manager(self):
        inst = _fresh_installer("FreeBSD")
        with patch.object(inst, "_detect_package_manager", return_value=None):
            assert inst.install_system_prerequisites() is True

    @pytest.mark.platform_macos
    def test_macos_installs_via_brew(self):
        inst = _fresh_installer("Darwin")
        inst._pkg_manager = "brew"
        with patch.object(inst, "_ensure_homebrew", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)):
            assert inst.install_system_prerequisites() is True

    @pytest.mark.platform_linux
    def test_apt_installs_build_tools(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "apt"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_system_prerequisites() is True

    @pytest.mark.platform_linux
    def test_dnf_installs_dev_packages(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "dnf"
        with patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_system_prerequisites() is True

    @pytest.mark.platform_linux
    def test_pacman_installs_base_devel(self):
        inst = _fresh_installer("Linux")
        inst._pkg_manager = "pacman"
        with patch.object(inst, "_run_command", return_value=_make_result(0)):
            assert inst.install_system_prerequisites() is True


# ============================================================================
# TestSetupDatabase
# ============================================================================

class TestSetupDatabase:

    @pytest.mark.platform_macos
    def test_macos_creates_user_and_db(self):
        inst = _fresh_installer("Darwin")
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.Path.glob", return_value=iter([])):
            assert inst.setup_database() is True

    @pytest.mark.platform_linux
    def test_linux_creates_user_and_db_via_sudo(self):
        inst = _fresh_installer("Linux")
        with patch("run.subprocess.run", return_value=_make_result(0)):
            assert inst.setup_database() is True

    @pytest.mark.platform_windows
    def test_windows_creates_user_and_db(self):
        inst = _fresh_installer("Windows")
        with patch.object(inst, "_is_command_available", return_value=True), \
             patch("run.subprocess.run", return_value=_make_result(0)):
            assert inst.setup_database() is True

    def test_exception_returns_false(self):
        inst = _fresh_installer("Darwin")
        with patch("run.subprocess.run", side_effect=OSError("connection refused")), \
             patch("run.Path.glob", return_value=iter([])):
            assert inst.setup_database() is False
