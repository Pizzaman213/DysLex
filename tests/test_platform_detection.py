"""Tests for PackageInstaller platform detection logic.

Covers _detect_package_manager() and _detect_linux_distro().
"""

import pytest
from unittest.mock import patch, mock_open

from run import PackageInstaller


# ============================================================================
# TestDetectPackageManager
# ============================================================================

class TestDetectPackageManager:
    """Tests for _detect_package_manager()."""

    def _fresh_installer(self, platform_name: str) -> PackageInstaller:
        inst = PackageInstaller(color_enabled=False, yes=True)
        inst.platform_name = platform_name
        return inst

    @pytest.mark.platform_macos
    def test_macos_returns_brew(self):
        inst = self._fresh_installer("Darwin")
        assert inst._detect_package_manager() == "brew"

    @pytest.mark.platform_windows
    def test_windows_returns_choco(self):
        inst = self._fresh_installer("Windows")
        assert inst._detect_package_manager() == "choco"

    @pytest.mark.platform_linux
    def test_ubuntu_returns_apt(self):
        inst = self._fresh_installer("Linux")
        content = "ID=ubuntu\nID_LIKE=debian\n"
        with patch.object(type(inst), '_detect_linux_distro', return_value='debian'):
            assert inst._detect_package_manager() == "apt"

    @pytest.mark.platform_linux
    def test_fedora_returns_dnf(self):
        inst = self._fresh_installer("Linux")
        with patch.object(type(inst), '_detect_linux_distro', return_value='fedora'):
            assert inst._detect_package_manager() == "dnf"

    @pytest.mark.platform_linux
    def test_arch_returns_pacman(self):
        inst = self._fresh_installer("Linux")
        with patch.object(type(inst), '_detect_linux_distro', return_value='arch'):
            assert inst._detect_package_manager() == "pacman"

    @pytest.mark.platform_linux
    def test_unknown_distro_returns_none(self):
        inst = self._fresh_installer("Linux")
        with patch.object(type(inst), '_detect_linux_distro', return_value=None):
            assert inst._detect_package_manager() is None

    def test_unknown_platform_returns_none(self):
        inst = self._fresh_installer("FreeBSD")
        assert inst._detect_package_manager() is None

    def test_caching_returns_same_result(self):
        inst = self._fresh_installer("Darwin")
        first = inst._detect_package_manager()
        # Change platform_name — should still return cached result
        inst.platform_name = "Linux"
        second = inst._detect_package_manager()
        assert first == second == "brew"


# ============================================================================
# TestDetectLinuxDistro
# ============================================================================

class TestDetectLinuxDistro:
    """Tests for _detect_linux_distro()."""

    def _fresh_installer(self) -> PackageInstaller:
        inst = PackageInstaller(color_enabled=False, yes=True)
        inst.platform_name = "Linux"
        return inst

    @pytest.mark.parametrize("distro_id,expected_family", [
        ("ubuntu", "debian"),
        ("debian", "debian"),
        ("pop", "debian"),
        ("linuxmint", "debian"),
        ("elementary", "debian"),
        ("zorin", "debian"),
        ("fedora", "fedora"),
        ("rhel", "fedora"),
        ("centos", "fedora"),
        ("rocky", "fedora"),
        ("alma", "fedora"),
        ("arch", "arch"),
        ("manjaro", "arch"),
        ("endeavouros", "arch"),
    ])
    @pytest.mark.platform_linux
    def test_distro_id_maps_to_family(self, distro_id, expected_family):
        inst = self._fresh_installer()
        content = f"ID={distro_id}\n"
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            assert inst._detect_linux_distro() == expected_family

    @pytest.mark.parametrize("distro_id,id_like,expected_family", [
        ("neon", "ubuntu debian", "debian"),
        ("nobara", "fedora", "fedora"),
        ("garuda", "arch", "arch"),
        ("unknown", "rhel fedora", "fedora"),
    ])
    @pytest.mark.platform_linux
    def test_id_like_fallback(self, distro_id, id_like, expected_family):
        inst = self._fresh_installer()
        content = f"ID={distro_id}\nID_LIKE={id_like}\n"
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            assert inst._detect_linux_distro() == expected_family

    @pytest.mark.platform_linux
    def test_missing_os_release_returns_none(self):
        inst = self._fresh_installer()
        with patch("run.Path.exists", return_value=False):
            assert inst._detect_linux_distro() is None

    @pytest.mark.platform_linux
    def test_empty_os_release_returns_none(self):
        inst = self._fresh_installer()
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="")):
            assert inst._detect_linux_distro() is None

    @pytest.mark.platform_linux
    def test_unknown_distro_returns_none(self):
        inst = self._fresh_installer()
        content = "ID=gentoo\n"
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            assert inst._detect_linux_distro() is None

    @pytest.mark.platform_linux
    def test_caching_returns_same_result(self):
        inst = self._fresh_installer()
        content = "ID=ubuntu\n"
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            first = inst._detect_linux_distro()

        # Now change os-release — should return cached result
        different_content = "ID=fedora\n"
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=different_content)):
            second = inst._detect_linux_distro()

        assert first == second == "debian"

    @pytest.mark.platform_linux
    def test_quoted_values_handled(self):
        inst = self._fresh_installer()
        content = 'ID="ubuntu"\nID_LIKE="debian"\n'
        with patch("run.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=content)):
            assert inst._detect_linux_distro() == "debian"
