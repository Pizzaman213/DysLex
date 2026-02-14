"""Tests for NPU provider detection and session management."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.npu_provider import (
    PROVIDER_PRIORITY,
    create_session,
    detect_available_providers,
    get_active_provider,
    get_provider_options,
    select_providers,
)


class TestDetectAvailableProviders:
    """Tests for detect_available_providers()."""

    def test_cpu_always_available(self):
        """CPUExecutionProvider should always be in the detected list."""
        providers = detect_available_providers()
        assert "CPUExecutionProvider" in providers

    def test_returns_list(self):
        providers = detect_available_providers()
        assert isinstance(providers, list)
        assert len(providers) >= 1

    def test_priority_order_preserved(self):
        """Returned providers should follow PROVIDER_PRIORITY order."""
        providers = detect_available_providers()
        indices = [PROVIDER_PRIORITY.index(p) for p in providers]
        assert indices == sorted(indices)

    @patch("app.core.npu_provider.ort")
    def test_filters_to_known_providers(self, mock_ort):
        mock_ort.get_available_providers.return_value = [
            "CPUExecutionProvider",
            "SomeUnknownProvider",
        ]
        providers = detect_available_providers()
        assert "CPUExecutionProvider" in providers
        assert "SomeUnknownProvider" not in providers


class TestGetProviderOptions:
    """Tests for get_provider_options()."""

    def test_cpu_returns_empty(self):
        opts = get_provider_options("CPUExecutionProvider")
        assert opts == {}

    def test_coreml_returns_empty(self):
        opts = get_provider_options("CoreMLExecutionProvider")
        assert opts == {}

    def test_cuda_has_device_id(self):
        opts = get_provider_options("CUDAExecutionProvider")
        assert opts.get("device_id") == 0

    def test_unknown_provider_returns_empty(self):
        opts = get_provider_options("FakeProvider")
        assert opts == {}

    def test_returns_copy(self):
        """Modifying returned dict should not affect internal state."""
        opts = get_provider_options("CoreMLExecutionProvider")
        opts["extra"] = "value"
        assert "extra" not in get_provider_options("CoreMLExecutionProvider")


class TestSelectProviders:
    """Tests for select_providers()."""

    def test_override_string(self):
        providers = select_providers("CoreMLExecutionProvider,CPUExecutionProvider")
        assert providers == ["CoreMLExecutionProvider", "CPUExecutionProvider"]

    def test_override_always_appends_cpu(self):
        providers = select_providers("CoreMLExecutionProvider")
        assert providers[-1] == "CPUExecutionProvider"

    def test_override_does_not_duplicate_cpu(self):
        providers = select_providers("CPUExecutionProvider")
        assert providers.count("CPUExecutionProvider") == 1

    def test_none_override_auto_detects(self):
        providers = select_providers(None)
        assert "CPUExecutionProvider" in providers

    def test_empty_string_auto_detects(self):
        providers = select_providers("")
        assert "CPUExecutionProvider" in providers

    def test_env_var_override(self):
        with patch.dict(os.environ, {"DYSLEX_ONNX_PROVIDERS": "CUDAExecutionProvider"}):
            providers = select_providers(None)
            assert providers[0] == "CUDAExecutionProvider"
            assert "CPUExecutionProvider" in providers

    def test_explicit_override_beats_env_var(self):
        with patch.dict(os.environ, {"DYSLEX_ONNX_PROVIDERS": "CUDAExecutionProvider"}):
            providers = select_providers("CPUExecutionProvider")
            assert providers == ["CPUExecutionProvider"]

    def test_whitespace_handling(self):
        providers = select_providers("  CoreMLExecutionProvider , CPUExecutionProvider  ")
        assert providers == ["CoreMLExecutionProvider", "CPUExecutionProvider"]


class TestCreateSession:
    """Tests for create_session()."""

    def test_fallback_to_cpu(self):
        """With a fake provider first, should fall back to CPU."""
        from pathlib import Path

        model_path = Path("ml/models/quick_correction_base_v1/model.onnx")
        if not model_path.exists():
            pytest.skip("ONNX model not available")

        session, provider = create_session(
            str(model_path),
            providers=["FakeNonexistentProvider", "CPUExecutionProvider"],
        )
        assert provider == "CPUExecutionProvider"
        assert session is not None

    def test_cpu_only(self):
        """CPUExecutionProvider should always work."""
        from pathlib import Path

        model_path = Path("ml/models/quick_correction_base_v1/model.onnx")
        if not model_path.exists():
            pytest.skip("ONNX model not available")

        session, provider = create_session(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        assert provider == "CPUExecutionProvider"

    def test_all_providers_fail_raises(self):
        """If every provider fails, should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="All ONNX providers failed"):
            create_session(
                "/nonexistent/model.onnx",
                providers=["CPUExecutionProvider"],
            )

    def test_default_providers_used_when_none(self):
        """When providers=None, select_providers() is called."""
        from pathlib import Path

        model_path = Path("ml/models/quick_correction_base_v1/model.onnx")
        if not model_path.exists():
            pytest.skip("ONNX model not available")

        session, provider = create_session(str(model_path), providers=None)
        assert provider in PROVIDER_PRIORITY


class TestGetActiveProvider:
    """Tests for get_active_provider()."""

    def test_returns_string(self):
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ["CPUExecutionProvider"]
        assert get_active_provider(mock_session) == "CPUExecutionProvider"

    def test_returns_first_provider(self):
        mock_session = MagicMock()
        mock_session.get_providers.return_value = [
            "CoreMLExecutionProvider",
            "CPUExecutionProvider",
        ]
        assert get_active_provider(mock_session) == "CoreMLExecutionProvider"

    def test_empty_providers(self):
        mock_session = MagicMock()
        mock_session.get_providers.return_value = []
        assert get_active_provider(mock_session) == "unknown"
