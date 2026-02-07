"""Tests for text-to-speech service."""

import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.tts_service import (
    _content_hash,
    batch_text_to_speech,
    cleanup_old_audio_files,
    get_available_voices,
    text_to_speech,
)


# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------


class TestContentHash:
    """Tests for _content_hash."""

    def test_deterministic(self):
        h1 = _content_hash("hello world", "default")
        h2 = _content_hash("hello world", "default")
        assert h1 == h2

    def test_different_text_different_hash(self):
        h1 = _content_hash("hello", "default")
        h2 = _content_hash("world", "default")
        assert h1 != h2

    def test_different_voice_different_hash(self):
        h1 = _content_hash("hello", "voice-a")
        h2 = _content_hash("hello", "voice-b")
        assert h1 != h2

    def test_strips_and_lowercases(self):
        h1 = _content_hash("  Hello World  ", "default")
        h2 = _content_hash("hello world", "default")
        assert h1 == h2

    def test_returns_hex_string(self):
        h = _content_hash("text", "voice")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest


class TestGetAvailableVoices:
    """Tests for get_available_voices."""

    def test_returns_list(self):
        voices = get_available_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_each_voice_has_required_fields(self):
        voices = get_available_voices()
        for voice in voices:
            assert "id" in voice
            assert "name" in voice
            assert "language" in voice

    def test_contains_default_voice(self):
        voices = get_available_voices()
        ids = [v["id"] for v in voices]
        assert "default" in ids


# ---------------------------------------------------------------------------
# Mock-based async tests — text_to_speech
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTextToSpeech:
    """Tests for text_to_speech."""

    @patch("app.services.tts_service.settings")
    async def test_no_api_key_returns_empty(self, mock_settings):
        mock_settings.nvidia_nim_api_key = ""
        result = await text_to_speech("hello world")
        assert result == ""

    @patch("app.services.tts_service._call_tts_api", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_cache_hit_skips_api(self, mock_settings, mock_api, tmp_path):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_audio_base_url = "/audio"

        # Pre-create the cached file
        h = _content_hash("hello world", "default")
        cached_file = tmp_path / f"{h}.mp3"
        cached_file.write_bytes(b"fake audio data")

        result = await text_to_speech("hello world", "default")
        assert result == f"/audio/{h}.mp3"
        mock_api.assert_not_awaited()

    @patch("app.services.tts_service.aiofiles", create=True)
    @patch("app.services.tts_service._call_tts_api", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_cache_miss_calls_api(self, mock_settings, mock_api, mock_aiofiles, tmp_path):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_audio_base_url = "/audio"

        mock_response = MagicMock()
        mock_response.content = b"real audio bytes"
        mock_api.return_value = mock_response

        # Mock aiofiles.open as async context manager
        mock_file = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_file)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_aiofiles.open.return_value = mock_cm

        result = await text_to_speech("new text", "default")
        h = _content_hash("new text", "default")
        assert result == f"/audio/{h}.mp3"
        mock_api.assert_awaited_once()

    @patch("app.services.tts_service._call_tts_api", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_api_failure_returns_empty(self, mock_settings, mock_api):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = "/tmp/test_tts_nonexistent"
        mock_settings.tts_audio_base_url = "/audio"

        mock_api.side_effect = httpx.TimeoutException("timeout")

        result = await text_to_speech("hello", "default")
        assert result == ""


# ---------------------------------------------------------------------------
# Mock-based async tests — batch_text_to_speech
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBatchTextToSpeech:
    """Tests for batch_text_to_speech."""

    @patch("app.services.tts_service.settings")
    async def test_no_api_key_returns_empty_urls(self, mock_settings):
        mock_settings.nvidia_nim_api_key = ""
        sentences = [{"index": 0, "text": "hello"}, {"index": 1, "text": "world"}]
        result = await batch_text_to_speech(sentences)
        assert len(result) == 2
        assert all(r["audio_url"] == "" for r in result)

    @patch("app.services.tts_service._generate_and_cache", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_cached_files_detected(self, mock_settings, mock_gen, tmp_path):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_audio_base_url = "/audio"

        # Pre-cache one sentence
        h = _content_hash("cached sentence", "default")
        (tmp_path / f"{h}.mp3").write_bytes(b"audio")

        sentences = [
            {"index": 0, "text": "cached sentence"},
            {"index": 1, "text": "uncached sentence"},
        ]

        mock_gen.return_value = "/audio/new.mp3"

        result = await batch_text_to_speech(sentences, "default")
        assert len(result) == 2
        assert result[0]["cached"] is True
        assert result[0]["audio_url"] == f"/audio/{h}.mp3"


# ---------------------------------------------------------------------------
# cleanup_old_audio_files
# ---------------------------------------------------------------------------


class TestCleanupOldAudioFiles:
    """Tests for cleanup_old_audio_files."""

    @patch("app.services.tts_service.settings")
    def test_disabled_cleanup_does_nothing(self, mock_settings, tmp_path):
        mock_settings.tts_cleanup_enabled = False
        mock_settings.tts_audio_dir = str(tmp_path)

        (tmp_path / "test.mp3").write_bytes(b"data")
        cleanup_old_audio_files()
        assert (tmp_path / "test.mp3").exists()

    @patch("app.services.tts_service.settings")
    def test_nonexistent_dir_does_nothing(self, mock_settings):
        mock_settings.tts_cleanup_enabled = True
        mock_settings.tts_audio_dir = "/nonexistent/path/audio"
        # Should not raise
        cleanup_old_audio_files()

    @patch("app.services.tts_service.settings")
    def test_removes_old_files(self, mock_settings, tmp_path):
        mock_settings.tts_cleanup_enabled = True
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_cache_ttl = 60  # 60 seconds

        # Create an old file with old metadata
        mp3 = tmp_path / "old.mp3"
        mp3.write_bytes(b"audio")
        meta = tmp_path / "old.mp3.meta"
        meta.write_text(str(time.time() - 120))  # 2 minutes ago

        cleanup_old_audio_files()
        assert not mp3.exists()
        assert not meta.exists()

    @patch("app.services.tts_service.settings")
    def test_keeps_recent_files(self, mock_settings, tmp_path):
        mock_settings.tts_cleanup_enabled = True
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_cache_ttl = 3600  # 1 hour

        mp3 = tmp_path / "recent.mp3"
        mp3.write_bytes(b"audio")
        meta = tmp_path / "recent.mp3.meta"
        meta.write_text(str(time.time()))  # just now

        cleanup_old_audio_files()
        assert mp3.exists()
        assert meta.exists()
