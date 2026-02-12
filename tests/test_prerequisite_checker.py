"""Tests for PrerequisiteChecker orchestration and individual checks."""

import sys
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from run import PrerequisiteChecker, CheckError, CheckWarning, CheckSkipped


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _make_checker(mode="dev", auto_setup=False, yes=True, **kwargs) -> PrerequisiteChecker:
    config = {
        "auto_setup": auto_setup,
        "yes": yes,
        "backend_port": kwargs.get("backend_port", 8000),
        "frontend_port": kwargs.get("frontend_port", 3000),
        "kill_ports": kwargs.get("kill_ports", False),
    }
    return PrerequisiteChecker(mode=mode, config=config, color_enabled=False)


# ============================================================================
# TestCheckAll
# ============================================================================

class TestCheckAll:

    def test_dev_mode_runs_all_checks(self):
        checker = _make_checker(mode="dev")
        with patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service"), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True
            assert len(checker.errors) == 0

    def test_docker_mode_checks_docker(self):
        checker = _make_checker(mode="docker")
        with patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_docker_availability"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True

    def test_backend_only_skips_frontend_checks(self):
        checker = _make_checker(mode="backend")
        with patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service"), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api") as mock_nvidia:
            result = checker.check_all()
            assert result is True

    def test_frontend_only_skips_backend_checks(self):
        checker = _make_checker(mode="frontend")
        with patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True

    def test_returns_false_on_critical_error(self):
        checker = _make_checker(mode="dev")
        with patch.object(checker, "check_python_version", side_effect=CheckError("too old")), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service"), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is False
            assert len(checker.errors) == 1

    def test_returns_true_with_warnings_only(self):
        checker = _make_checker(mode="dev")
        with patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service", side_effect=CheckWarning("no redis")), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True
            assert len(checker.warnings) == 1

    def test_auto_setup_calls_install_system_prerequisites(self):
        checker = _make_checker(mode="dev", auto_setup=True)
        with patch.object(checker.installer, "install_system_prerequisites") as mock_sys, \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service"), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            checker.check_all()
            mock_sys.assert_called_once()


# ============================================================================
# TestCheckPythonVersion
# ============================================================================

class TestCheckPythonVersion:

    def test_passes_with_valid_version(self):
        checker = _make_checker()
        with patch("run.sys.version_info", (3, 12, 0)):
            checker.check_python_version()

    def test_fails_with_old_version(self):
        checker = _make_checker()
        with patch("run.sys.version_info", (3, 10, 0)):
            with pytest.raises(CheckError, match="Python 3.11"):
                checker.check_python_version()


# ============================================================================
# TestCheckNodeVersion
# ============================================================================

class TestCheckNodeVersion:

    def test_passes_with_valid_version(self):
        checker = _make_checker()
        with patch("run.subprocess.run", return_value=_make_result(0, stdout="v20.11.0")):
            checker.check_node_version()

    def test_fails_with_old_version_no_auto_setup(self):
        checker = _make_checker(auto_setup=False)
        with patch("run.subprocess.run", return_value=_make_result(0, stdout="v18.0.0")):
            with pytest.raises(CheckError, match="Node.js 20"):
                checker.check_node_version()

    def test_fails_when_not_installed_no_auto_setup(self):
        checker = _make_checker(auto_setup=False)
        with patch("run.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CheckError, match="Node.js 20"):
                checker.check_node_version()

    def test_auto_installs_when_missing(self):
        checker = _make_checker(auto_setup=True)
        with patch("run.subprocess.run", side_effect=FileNotFoundError), \
             patch.object(checker.installer, "install_node", return_value=True):
            checker.check_node_version()  # Should not raise

    def test_auto_install_failure_raises_error(self):
        checker = _make_checker(auto_setup=True)
        with patch("run.subprocess.run", side_effect=FileNotFoundError), \
             patch.object(checker.installer, "install_node", return_value=False):
            with pytest.raises(CheckError, match="Failed to install"):
                checker.check_node_version()


# ============================================================================
# TestCheckPostgresService
# ============================================================================

class TestCheckPostgresService:

    def test_passes_when_port_open(self):
        checker = _make_checker()
        with patch.object(checker, "_is_port_open", return_value=True):
            checker.check_postgres_service()

    def test_fails_when_port_closed_no_auto_setup(self):
        checker = _make_checker(auto_setup=False)
        with patch.object(checker, "_is_port_open", return_value=False):
            with pytest.raises(CheckError, match="not running"):
                checker.check_postgres_service()

    def test_auto_starts_when_port_closed(self):
        checker = _make_checker(auto_setup=True)
        with patch.object(checker.installer, "_is_postgres_installed", return_value=True), \
             patch.object(checker, "_is_port_open", return_value=False), \
             patch.object(checker, "_start_postgres", return_value=True):
            checker.check_postgres_service()
            assert "postgresql" in checker.services_started

    def test_auto_install_then_start(self):
        checker = _make_checker(auto_setup=True)
        with patch.object(checker.installer, "_is_postgres_installed", return_value=False), \
             patch.object(checker.installer, "install_postgres", return_value=True), \
             patch.object(checker, "_is_port_open", return_value=False), \
             patch.object(checker, "_start_postgres", return_value=True):
            checker.check_postgres_service()

    def test_auto_install_failure_raises_error(self):
        checker = _make_checker(auto_setup=True)
        with patch.object(checker.installer, "_is_postgres_installed", return_value=False), \
             patch.object(checker.installer, "install_postgres", return_value=False):
            with pytest.raises(CheckError, match="Failed to install"):
                checker.check_postgres_service()


# ============================================================================
# TestCheckRedisService
# ============================================================================

class TestCheckRedisService:

    def test_passes_when_port_open(self):
        checker = _make_checker()
        with patch.object(checker, "_is_port_open", return_value=True):
            checker.check_redis_service()

    def test_warning_when_port_closed_no_auto_setup(self):
        checker = _make_checker(auto_setup=False)
        with patch.object(checker, "_is_port_open", return_value=False):
            with pytest.raises(CheckWarning, match="not running"):
                checker.check_redis_service()

    def test_auto_starts_when_port_closed(self):
        checker = _make_checker(auto_setup=True)
        with patch.object(checker.installer, "_is_redis_installed", return_value=True), \
             patch.object(checker, "_is_port_open", return_value=False), \
             patch.object(checker, "_start_redis", return_value=True):
            checker.check_redis_service()
            assert "redis" in checker.services_started


# ============================================================================
# TestStartPostgres
# ============================================================================

class TestStartPostgres:

    @pytest.mark.platform_macos
    def test_macos_starts_via_brew_services(self):
        checker = _make_checker()
        checker.platform_name = "Darwin"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_open", return_value=True):
            assert checker._start_postgres() is True

    @pytest.mark.platform_linux
    def test_linux_starts_via_systemctl(self):
        checker = _make_checker()
        checker.platform_name = "Linux"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_open", return_value=True):
            assert checker._start_postgres() is True


# ============================================================================
# TestStartRedis
# ============================================================================

class TestStartRedis:

    @pytest.mark.platform_macos
    def test_macos_starts_via_brew_services(self):
        checker = _make_checker()
        checker.platform_name = "Darwin"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_open", return_value=True):
            assert checker._start_redis() is True

    @pytest.mark.platform_linux
    def test_linux_starts_via_systemctl(self):
        checker = _make_checker()
        checker.platform_name = "Linux"
        with patch("run.subprocess.run", return_value=_make_result(0)), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_open", return_value=True):
            assert checker._start_redis() is True

    @pytest.mark.platform_linux
    def test_linux_fallback_to_direct_start(self):
        checker = _make_checker()
        checker.platform_name = "Linux"

        call_count = [0]
        def side_effect(cmd, **kwargs):
            call_count[0] += 1
            # systemctl fails for both service names
            if isinstance(cmd, list) and "systemctl" in cmd:
                return _make_result(1)
            return _make_result(0)

        with patch("run.subprocess.run", side_effect=side_effect), \
             patch("run.subprocess.Popen") as mock_popen, \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_open", return_value=True):
            assert checker._start_redis() is True
            mock_popen.assert_called_once()


# ============================================================================
# TestKillPortProcess
# ============================================================================

class TestKillPortProcess:

    def test_unix_uses_lsof(self):
        checker = _make_checker()
        checker.platform_name = "Darwin"
        with patch("run.subprocess.run", return_value=_make_result(0, stdout="12345")), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_available", return_value=True):
            assert checker._kill_port_process(8000) is True

    @pytest.mark.platform_windows
    def test_windows_uses_netstat(self):
        checker = _make_checker()
        checker.platform_name = "Windows"
        output = "  TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    12345"
        with patch("run.subprocess.run", return_value=_make_result(0, stdout=output)), \
             patch("run.time.sleep"), \
             patch.object(checker, "_is_port_available", return_value=True):
            assert checker._kill_port_process(8000) is True


# ============================================================================
# TestCheckDockerAvailability
# ============================================================================

class TestCheckDockerAvailability:

    def test_passes_when_docker_available(self):
        checker = _make_checker(mode="docker")
        with patch("run.subprocess.run", return_value=_make_result(0)):
            checker.check_docker_availability()

    def test_fails_when_docker_not_found(self):
        checker = _make_checker(mode="docker")
        with patch("run.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CheckError, match="Docker not found"):
                checker.check_docker_availability()

    def test_fails_when_docker_daemon_not_running(self):
        checker = _make_checker(mode="docker")
        call_count = [0]
        def side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # docker --version
                return _make_result(0)
            else:  # docker info
                return _make_result(1)

        with patch("run.subprocess.run", side_effect=side_effect):
            with pytest.raises(CheckError, match="daemon"):
                checker.check_docker_availability()
