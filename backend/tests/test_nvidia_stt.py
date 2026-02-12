"""Tests for NVIDIA NIM ASR transcription (gRPC client, service, and factory)."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.grpc_stt_client import (
    _encode_bool_field,
    _encode_bytes_field,
    _encode_recognition_config,
    _encode_recognize_request,
    _encode_string_field,
    _encode_varint,
    _encode_varint_field,
    _extract_transcript,
    _read_varint,
)


# ---------------------------------------------------------------------------
# grpc_stt_client — protobuf encoding helpers
# ---------------------------------------------------------------------------


class TestVarintEncoding:
    """Tests for varint encode/decode."""

    def test_encode_small_value(self):
        assert _encode_varint(1) == b"\x01"

    def test_encode_zero(self):
        assert _encode_varint(0) == b"\x00"

    def test_encode_large_value(self):
        # 300 = 0b100101100 → two bytes: 0xAC 0x02
        result = _encode_varint(300)
        assert len(result) == 2

    def test_roundtrip(self):
        for val in [0, 1, 127, 128, 300, 16000, 65535]:
            encoded = _encode_varint(val)
            decoded, end_pos = _read_varint(encoded, 0)
            assert decoded == val
            assert end_pos == len(encoded)


class TestFieldEncoding:
    """Tests for protobuf field encoding helpers."""

    def test_string_field(self):
        result = _encode_string_field(1, "hello")
        # tag = (1 << 3) | 2 = 0x0A, length = 5, data = "hello"
        assert result[0] == 0x0A
        assert result[1] == 5
        assert result[2:] == b"hello"

    def test_varint_field(self):
        result = _encode_varint_field(1, 1)
        # tag = (1 << 3) | 0 = 0x08, value = 0x01
        assert result == b"\x08\x01"

    def test_bytes_field(self):
        result = _encode_bytes_field(2, b"\xff\x00")
        # tag = (2 << 3) | 2 = 0x12, length = 2
        assert result[0] == 0x12
        assert result[1] == 2
        assert result[2:] == b"\xff\x00"

    def test_bool_field_true(self):
        result = _encode_bool_field(11, True)
        assert result == _encode_varint_field(11, 1)

    def test_bool_field_false(self):
        result = _encode_bool_field(11, False)
        assert result == _encode_varint_field(11, 0)


class TestRecognitionConfig:
    """Tests for RecognitionConfig encoding."""

    def test_produces_bytes(self):
        result = _encode_recognition_config(
            encoding=1,
            sample_rate_hz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_contains_language_code(self):
        result = _encode_recognition_config(1, 16000, "en-US", True)
        assert b"en-US" in result


class TestRecognizeRequest:
    """Tests for RecognizeRequest encoding."""

    def test_produces_bytes(self):
        config = _encode_recognition_config(1, 16000, "en-US", True)
        audio = b"\x00\x01\x02\x03"
        result = _encode_recognize_request(config, audio)
        assert isinstance(result, bytes)
        assert len(result) > len(config) + len(audio)

    def test_contains_audio(self):
        config = _encode_recognition_config(1, 16000, "en-US", True)
        audio = b"TESTAUDIO"
        result = _encode_recognize_request(config, audio)
        assert b"TESTAUDIO" in result


# ---------------------------------------------------------------------------
# grpc_stt_client — transcript extraction
# ---------------------------------------------------------------------------


class TestTranscriptExtraction:
    """Tests for _extract_transcript."""

    def test_empty_data(self):
        assert _extract_transcript(b"") == ""

    def test_extracts_from_valid_response(self):
        # Build a mock RecognizeResponse:
        # field 1 (results) -> field 1 (alternatives) -> field 1 (transcript)
        transcript = b"Hello world"
        # SpeechRecognitionAlternative: field 1 = transcript string
        alt = _encode_string_field(1, "Hello world")
        # SpeechRecognitionResult: field 1 = alternative sub-message
        result_msg = (
            _encode_varint((1 << 3) | 2)
            + _encode_varint(len(alt))
            + alt
        )
        # RecognizeResponse: field 1 = result sub-message
        response = (
            _encode_varint((1 << 3) | 2)
            + _encode_varint(len(result_msg))
            + result_msg
        )
        assert _extract_transcript(response) == "Hello world"


# ---------------------------------------------------------------------------
# nvidia_stt_service — NvidiaTranscriptionService
# ---------------------------------------------------------------------------


class TestNvidiaTranscriptionService:
    """Tests for NvidiaTranscriptionService."""

    @patch("app.services.nvidia_stt_service.settings")
    def test_detects_cloud_url(self, mock_settings):
        mock_settings.nvidia_nim_stt_url = "https://integrate.api.nvidia.com/v1"
        mock_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_settings.nvidia_nim_api_key = "test-key"

        # Reset the logged flag so constructor can log
        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        svc = NvidiaTranscriptionService()
        assert svc._is_cloud is True

    @patch("app.services.nvidia_stt_service.settings")
    def test_detects_selfhosted_url(self, mock_settings):
        mock_settings.nvidia_nim_stt_url = "http://localhost:9000/v1"
        mock_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_settings.nvidia_nim_api_key = "test-key"

        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        svc = NvidiaTranscriptionService()
        assert svc._is_cloud is False

    @pytest.mark.asyncio
    @patch("app.services.nvidia_stt_service.settings")
    async def test_transcribe_cloud_path(self, mock_settings):
        mock_settings.nvidia_nim_stt_url = "https://integrate.api.nvidia.com/v1"
        mock_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_settings.nvidia_nim_api_key = "test-key"

        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        svc = NvidiaTranscriptionService()

        with patch.object(svc, "_transcribe_cloud", new_callable=AsyncMock) as mock_cloud:
            mock_cloud.return_value = "Hello from the cloud"
            audio = io.BytesIO(b"fake audio data")
            result = await svc.transcribe_audio(audio, "test.wav", "en")

            assert result.transcript == "Hello from the cloud"
            mock_cloud.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.nvidia_stt_service.settings")
    async def test_transcribe_selfhosted_path(self, mock_settings):
        mock_settings.nvidia_nim_stt_url = "http://localhost:9000/v1"
        mock_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_settings.nvidia_nim_api_key = "test-key"

        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        svc = NvidiaTranscriptionService()

        with patch.object(svc, "_transcribe_selfhosted", new_callable=AsyncMock) as mock_sh:
            mock_sh.return_value = "Hello from self-hosted"
            audio = io.BytesIO(b"fake audio data")
            result = await svc.transcribe_audio(audio, "test.wav", "en")

            assert result.transcript == "Hello from self-hosted"
            mock_sh.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.nvidia_stt_service.settings")
    async def test_transcribe_failure_returns_empty(self, mock_settings):
        mock_settings.nvidia_nim_stt_url = "https://integrate.api.nvidia.com/v1"
        mock_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_settings.nvidia_nim_api_key = "test-key"

        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        svc = NvidiaTranscriptionService()

        with patch.object(svc, "_transcribe_cloud", new_callable=AsyncMock) as mock_cloud:
            mock_cloud.side_effect = RuntimeError("gRPC failure")
            audio = io.BytesIO(b"fake audio data")
            result = await svc.transcribe_audio(audio, "test.wav")

            assert result.transcript == ""


# ---------------------------------------------------------------------------
# transcription_service — factory function
# ---------------------------------------------------------------------------


class TestTranscriptionFactory:
    """Tests for _create_transcription_service factory."""

    @patch("app.services.transcription_service.settings")
    def test_default_returns_faster_whisper(self, mock_settings):
        mock_settings.stt_provider = "faster-whisper"
        mock_settings.transcription_url = "http://localhost:8786/v1"
        mock_settings.nvidia_nim_api_key = ""

        from app.services.transcription_service import (
            TranscriptionService,
            _create_transcription_service,
        )

        svc = _create_transcription_service()
        assert isinstance(svc, TranscriptionService)

    @patch("app.services.nvidia_stt_service.settings")
    @patch("app.services.transcription_service.settings")
    def test_nvidia_returns_nvidia_service(self, mock_ts_settings, mock_nv_settings):
        mock_ts_settings.stt_provider = "nvidia"

        mock_nv_settings.nvidia_nim_stt_url = "http://localhost:9000/v1"
        mock_nv_settings.nvidia_nim_stt_model = "nvidia/parakeet-ctc-0.6b-asr"
        mock_nv_settings.nvidia_nim_api_key = "test-key"

        import app.services.nvidia_stt_service as mod
        mod._startup_logged = False

        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        from app.services.transcription_service import _create_transcription_service

        svc = _create_transcription_service()
        assert isinstance(svc, NvidiaTranscriptionService)

    @patch("app.services.transcription_service.settings")
    def test_case_insensitive_provider(self, mock_settings):
        mock_settings.stt_provider = "FASTER-WHISPER"
        mock_settings.transcription_url = "http://localhost:8786/v1"
        mock_settings.nvidia_nim_api_key = ""

        from app.services.transcription_service import (
            TranscriptionService,
            _create_transcription_service,
        )

        svc = _create_transcription_service()
        assert isinstance(svc, TranscriptionService)


# ---------------------------------------------------------------------------
# nvidia_stt_service — language code mapping
# ---------------------------------------------------------------------------


class TestBcp47Mapping:
    """Tests for _to_bcp47 language code conversion."""

    def test_short_code_en(self):
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        assert NvidiaTranscriptionService._to_bcp47("en") == "en-US"

    def test_short_code_es(self):
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        assert NvidiaTranscriptionService._to_bcp47("es") == "es-US"

    def test_already_bcp47(self):
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        assert NvidiaTranscriptionService._to_bcp47("en-US") == "en-US"

    def test_underscore_format(self):
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        assert NvidiaTranscriptionService._to_bcp47("en_US") == "en-US"

    def test_unknown_code(self):
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        assert NvidiaTranscriptionService._to_bcp47("ja") == "ja-JA"
