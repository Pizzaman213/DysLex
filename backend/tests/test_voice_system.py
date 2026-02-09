"""System tests for STT (TranscriptionService, StreamingTranscriptionService) and TTS pipelines.

These tests use real (but minimal) audio fixture files and mock only the
external HTTP boundary (faster-whisper API, NVIDIA Riva API).
"""

import asyncio
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.capture import TranscriptionResponse
from app.services.transcription_service import TranscriptionService


# ---------------------------------------------------------------------------
# TranscriptionService — STT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTranscribeWav:
    """Transcription with a valid WAV fixture."""

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_wav_returns_transcript(self, mock_client_cls, wav_fixture):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "text": "hello world",
            "language": "en",
            "duration": 0.1,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            result = await service.transcribe_audio(f, "test.wav")

        assert isinstance(result, TranscriptionResponse)
        assert result.transcript == "hello world"
        assert result.language == "en"
        assert result.duration == 0.1

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_wav_sends_correct_content_type(self, mock_client_cls, wav_fixture):
        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "ok", "language": "en", "duration": 0.1}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            await service.transcribe_audio(f, "recording.wav")

        # Inspect the files kwarg passed to client.post
        call_kwargs = mock_client.post.call_args
        files = call_kwargs.kwargs.get("files") or call_kwargs[1].get("files")
        # files = {"file": (filename, file_obj, content_type)}
        assert files["file"][2] == "audio/wav"


@pytest.mark.asyncio
class TestTranscribeWebm:
    """Transcription with a WebM fixture."""

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_webm_returns_transcript(self, mock_client_cls, webm_fixture):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "text": "testing webm",
            "language": "en",
            "duration": 0.5,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(webm_fixture, "rb") as f:
            result = await service.transcribe_audio(f, "stream.webm")

        assert result.transcript == "testing webm"
        assert result.language == "en"


class TestTranscribeContentTypeMapping:
    """Filename extensions map to correct MIME types."""

    def test_wav_maps_to_audio_wav(self):
        service = TranscriptionService()
        assert service._get_content_type("recording.wav") == "audio/wav"

    def test_webm_maps_to_audio_webm(self):
        service = TranscriptionService()
        assert service._get_content_type("stream.webm") == "audio/webm"

    def test_mp3_maps_to_audio_mpeg(self):
        service = TranscriptionService()
        assert service._get_content_type("audio.mp3") == "audio/mpeg"

    def test_ogg_maps_to_audio_ogg(self):
        service = TranscriptionService()
        assert service._get_content_type("voice.ogg") == "audio/ogg"

    def test_flac_maps_to_audio_flac(self):
        service = TranscriptionService()
        assert service._get_content_type("music.flac") == "audio/flac"

    def test_m4a_maps_to_audio_mp4(self):
        service = TranscriptionService()
        assert service._get_content_type("voice.m4a") == "audio/mp4"

    def test_unknown_extension_defaults_to_webm(self):
        service = TranscriptionService()
        assert service._get_content_type("audio.xyz") == "audio/webm"


@pytest.mark.asyncio
class TestTranscribeErrorHandling:
    """Error handling for TranscriptionService."""

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_api_failure_returns_empty(self, mock_client_cls, wav_fixture):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            result = await service.transcribe_audio(f, "test.wav")

        assert result.transcript == ""
        assert result.language is None
        assert result.duration is None

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_timeout_returns_empty(self, mock_client_cls, wav_fixture):
        """TimeoutException after retries returns empty TranscriptionResponse."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            result = await service.transcribe_audio(f, "test.wav")

        assert result.transcript == ""

    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_retry_on_timeout_succeeds(self, mock_client_cls, wav_fixture):
        """Timeout on first call, success on retry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "recovered", "language": "en", "duration": 0.1}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[httpx.TimeoutException("timed out"), mock_response]
        )
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            result = await service.transcribe_audio(f, "test.wav")

        assert result.transcript == "recovered"
        assert mock_client.post.call_count == 2


@pytest.mark.asyncio
class TestTranscribeAuth:
    """Authentication header behavior."""

    @patch("app.services.transcription_service.settings")
    @patch("app.services.transcription_service.httpx.AsyncClient")
    async def test_transcribe_no_auth_for_localhost(
        self, mock_client_cls, mock_settings, wav_fixture
    ):
        """Local URL skips Authorization header."""
        mock_settings.transcription_url = "http://localhost:8786/v1"
        mock_settings.nvidia_nim_api_key = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "local", "language": "en", "duration": 0.1}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        service = TranscriptionService()

        with open(wav_fixture, "rb") as f:
            await service.transcribe_audio(f, "test.wav")

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# StreamingTranscriptionService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStreamingTranscription:
    """Tests for StreamingTranscriptionService buffering and transcription."""

    async def test_stream_below_threshold_buffers(self):
        """A small chunk below the buffer threshold returns None (buffered)."""
        from app.services.streaming_transcription_service import StreamingTranscriptionService

        service = StreamingTranscriptionService()
        # 100 bytes is far below 2s of 48kHz 16-bit audio (192,000 bytes)
        result = await service.process_chunk(b"\x00" * 100)
        assert result is None
        assert len(service.chunk_buffer) == 100

    @patch("app.services.streaming_transcription_service.transcription_service")
    async def test_stream_above_threshold_transcribes(self, mock_ts):
        """Enough audio to exceed threshold triggers transcription."""
        from app.services.streaming_transcription_service import StreamingTranscriptionService

        mock_ts.transcribe_audio = AsyncMock(
            return_value=TranscriptionResponse(transcript="hello", language="en", duration=2.0)
        )

        service = StreamingTranscriptionService()
        # 2 seconds at 48kHz, 16-bit = 192,000 bytes
        big_chunk = b"\x00" * (service.bytes_per_second * 2)
        result = await service.process_chunk(big_chunk)

        assert result is not None
        assert result["text"] == "hello"
        mock_ts.transcribe_audio.assert_awaited_once()

    @patch("app.services.streaming_transcription_service.transcription_service")
    async def test_stream_finalize_flushes_buffer(self, mock_ts):
        """finalize() processes remaining buffer."""
        from app.services.streaming_transcription_service import StreamingTranscriptionService

        mock_ts.transcribe_audio = AsyncMock(
            return_value=TranscriptionResponse(transcript="final words", language="en", duration=0.5)
        )

        service = StreamingTranscriptionService()
        # Add some data below threshold
        await service.process_chunk(b"\x00" * 1000)
        assert service.chunk_buffer == b"\x00" * 1000

        result = await service.finalize()
        assert result["text"] == "final words"
        assert service.chunk_buffer == b""

    async def test_stream_finalize_empty_buffer(self):
        """finalize() on empty buffer returns empty text."""
        from app.services.streaming_transcription_service import StreamingTranscriptionService

        service = StreamingTranscriptionService()
        result = await service.finalize()
        assert result["text"] == ""

    @patch("app.services.streaming_transcription_service.transcription_service")
    async def test_stream_max_buffer_protection(self, mock_ts):
        """Oversized chunk forces early transcription to prevent unbounded growth."""
        from app.services.streaming_transcription_service import StreamingTranscriptionService

        mock_ts.transcribe_audio = AsyncMock(
            return_value=TranscriptionResponse(transcript="overflow", language="en", duration=5.0)
        )

        service = StreamingTranscriptionService()
        # Pre-fill buffer close to MAX_BUFFER_BYTES
        service.chunk_buffer = b"\x00" * (service.MAX_BUFFER_BYTES - 100)

        # This chunk would push over the limit
        big_chunk = b"\xff" * 200
        result = await service.process_chunk(big_chunk)

        assert result is not None
        assert result["text"] == "overflow"
        # After overflow handling, the new chunk becomes the buffer
        assert service.chunk_buffer == big_chunk


# ---------------------------------------------------------------------------
# TTS — extends existing test_tts_service.py coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTtsGeneratesFile:
    """TTS generates a WAV file on disk via mocked Riva API."""

    @patch("app.services.tts_service._call_tts_api_selfhosted", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_tts_generates_wav_file_on_disk(self, mock_settings, mock_api, tmp_path):
        from app.services.tts_service import text_to_speech

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_audio_base_url = "/audio"
        mock_settings.nvidia_nim_voice_url = "http://localhost:9000/v1"

        # Simulate Riva returning WAV bytes
        fake_wav = b"RIFF" + b"\x00" * 40 + b"WAVEfmt " + b"\x00" * 100
        mock_response = MagicMock()
        mock_response.content = fake_wav
        mock_api.return_value = mock_response

        url = await text_to_speech("test sentence", "default")

        assert url.startswith("/audio/")
        assert url.endswith(".wav")

        # Verify file was written to disk
        filename = url.split("/")[-1]
        filepath = tmp_path / filename
        assert filepath.exists()
        assert filepath.read_bytes() == fake_wav


@pytest.mark.asyncio
class TestTtsBatchConcurrent:
    """Batch TTS processes multiple sentences concurrently."""

    @patch("app.services.tts_service._call_tts_api_selfhosted", new_callable=AsyncMock)
    @patch("app.services.tts_service.settings")
    async def test_tts_batch_concurrent_generation(self, mock_settings, mock_api, tmp_path):
        from app.services.tts_service import batch_text_to_speech

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.tts_audio_dir = str(tmp_path)
        mock_settings.tts_audio_base_url = "/audio"
        mock_settings.nvidia_nim_voice_url = "http://localhost:9000/v1"

        call_count = 0

        async def fake_tts_api(text, voice):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.content = f"audio-{call_count}".encode()
            return mock_resp

        mock_api.side_effect = fake_tts_api

        sentences = [
            {"index": 0, "text": "first sentence"},
            {"index": 1, "text": "second sentence"},
            {"index": 2, "text": "third sentence"},
        ]

        results = await batch_text_to_speech(sentences, "default")

        assert len(results) == 3
        assert all(r["audio_url"] != "" for r in results)
        assert call_count == 3
