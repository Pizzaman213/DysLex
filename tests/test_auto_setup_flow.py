"""End-to-end auto-setup flow tests per platform (fully mocked)."""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from run import PrerequisiteChecker, PackageInstaller, CheckError, CheckWarning, CheckSkipped


def _make_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _make_checker(mode="dev", auto_setup=True, yes=True) -> PrerequisiteChecker:
    config = {
        "auto_setup": auto_setup,
        "yes": yes,
        "backend_port": 8000,
        "frontend_port": 3000,
        "kill_ports": False,
    }
    return PrerequisiteChecker(mode=mode, config=config, color_enabled=False)


# ============================================================================
# Helpers to patch all checks at once
# ============================================================================

def _patch_all_checks_passing(checker):
    """Return a list of context managers that make all checks pass."""
    return [
        patch.object(checker, "check_python_version"),
        patch.object(checker, "check_node_version"),
        patch.object(checker, "check_postgres_service"),
        patch.object(checker, "check_database_setup"),
        patch.object(checker, "check_redis_service"),
        patch.object(checker, "check_backend_dependencies"),
        patch.object(checker, "check_backend_port"),
        patch.object(checker, "check_frontend_dependencies"),
        patch.object(checker, "check_frontend_port"),
        patch.object(checker, "check_env_file"),
        patch.object(checker, "check_environment_variables"),
        patch.object(checker, "check_nvidia_api"),
    ]


class TestMacOSAutoSetup:
    """Simulate auto-setup on macOS — all installs via brew."""

    @pytest.mark.platform_macos
    def test_happy_path(self):
        checker = _make_checker()
        checker.platform_name = "Darwin"
        checker.installer.platform_name = "Darwin"

        patches = _patch_all_checks_passing(checker)
        with patch.object(checker.installer, "install_system_prerequisites", return_value=True):
            # Enter all patches
            for p in patches:
                p.__enter__()
            try:
                result = checker.check_all()
                assert result is True
                assert len(checker.errors) == 0
            finally:
                for p in reversed(patches):
                    p.__exit__(None, None, None)

    @pytest.mark.platform_macos
    def test_node_install_triggers_on_missing(self):
        checker = _make_checker()
        checker.platform_name = "Darwin"
        checker.installer.platform_name = "Darwin"

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version", side_effect=CheckError("no node")), \
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


class TestUbuntuAutoSetup:
    """Simulate auto-setup on Ubuntu — installs via apt."""

    @pytest.mark.platform_linux
    def test_happy_path(self):
        checker = _make_checker()
        checker.platform_name = "Linux"
        checker.installer.platform_name = "Linux"

        patches = _patch_all_checks_passing(checker)
        with patch.object(checker.installer, "install_system_prerequisites", return_value=True):
            for p in patches:
                p.__enter__()
            try:
                result = checker.check_all()
                assert result is True
                assert len(checker.errors) == 0
            finally:
                for p in reversed(patches):
                    p.__exit__(None, None, None)

    @pytest.mark.platform_linux
    def test_all_services_auto_start(self):
        """Verify that postgres and redis are added to services_started."""
        checker = _make_checker()
        checker.platform_name = "Linux"
        checker.installer.platform_name = "Linux"

        def fake_postgres_check():
            checker.services_started.append("postgresql")

        def fake_redis_check():
            checker.services_started.append("redis")

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service", side_effect=fake_postgres_check), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service", side_effect=fake_redis_check), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True
            assert "postgresql" in checker.services_started
            assert "redis" in checker.services_started


class TestWindowsAutoSetup:
    """Simulate auto-setup on Windows — installs via choco."""

    @pytest.mark.platform_windows
    def test_happy_path(self):
        checker = _make_checker()
        checker.platform_name = "Windows"
        checker.installer.platform_name = "Windows"

        patches = _patch_all_checks_passing(checker)
        with patch.object(checker.installer, "install_system_prerequisites", return_value=True):
            for p in patches:
                p.__enter__()
            try:
                result = checker.check_all()
                assert result is True
                assert len(checker.errors) == 0
            finally:
                for p in reversed(patches):
                    p.__exit__(None, None, None)


class TestPartialFailure:
    """Simulate partial failure scenarios."""

    def test_redis_failure_is_warning_only(self):
        checker = _make_checker()

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service", side_effect=CheckWarning("redis failed")), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables"), \
             patch.object(checker, "check_nvidia_api"):
            result = checker.check_all()
            assert result is True  # Warnings don't fail the setup
            assert len(checker.warnings) == 1
            assert len(checker.errors) == 0

    def test_postgres_failure_is_critical(self):
        checker = _make_checker()

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service", side_effect=CheckError("pg failed")), \
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

    def test_multiple_warnings_still_pass(self):
        checker = _make_checker()

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
             patch.object(checker, "check_python_version"), \
             patch.object(checker, "check_node_version"), \
             patch.object(checker, "check_postgres_service"), \
             patch.object(checker, "check_database_setup"), \
             patch.object(checker, "check_redis_service", side_effect=CheckWarning("redis")), \
             patch.object(checker, "check_backend_dependencies"), \
             patch.object(checker, "check_backend_port"), \
             patch.object(checker, "check_frontend_dependencies"), \
             patch.object(checker, "check_frontend_port"), \
             patch.object(checker, "check_env_file"), \
             patch.object(checker, "check_environment_variables", side_effect=CheckWarning("no key")), \
             patch.object(checker, "check_nvidia_api", side_effect=CheckWarning("api fail")):
            result = checker.check_all()
            assert result is True
            assert len(checker.warnings) == 3

    def test_skipped_checks_dont_count(self):
        checker = _make_checker()

        with patch.object(checker.installer, "install_system_prerequisites", return_value=True), \
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
             patch.object(checker, "check_nvidia_api", side_effect=CheckSkipped()):
            result = checker.check_all()
            assert result is True
            assert len(checker.errors) == 0
            assert len(checker.warnings) == 0
