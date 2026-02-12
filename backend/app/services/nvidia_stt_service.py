"""
NVIDIA NIM ASR transcription service (dual-mode: cloud gRPC or self-hosted HTTP).

Supports two modes:
  - Cloud API (integrate.api.nvidia.com): Uses gRPC via grpc_stt_client
  - Self-hosted NIM (e.g. localhost:9000): Uses HTTP POST /audio/transcriptions
    (OpenAI-compatible, same format as faster-whisper)
"""

import logging
from typing import BinaryIO
from urllib.parse import urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.capture import TranscriptionResponse

logger = logging.getLogger(__name__)

_CLOUD_HOSTS = {"integrate.api.nvidia.com", "api.nvidia.com", "api.nvcf.nvidia.com"}

_startup_logged = False


def _is_cloud_url(url: str) -> bool:
    """Check if the URL points at NVIDIA's cloud API (requires gRPC)."""
    try:
        host = urlparse(url).hostname or ""
        return host in _CLOUD_HOSTS
    except Exception:
        return False


class NvidiaTranscriptionService:
    """Handles audio transcription via NVIDIA NIM ASR (cloud or self-hosted)."""

    def __init__(self) -> None:
        self.base_url = settings.nvidia_nim_stt_url.rstrip("/")
        self.model = settings.nvidia_nim_stt_model
        self.api_key = settings.nvidia_nim_api_key or None
        self._is_cloud = _is_cloud_url(self.base_url)

        global _startup_logged
        if not _startup_logged:
            mode = "cloud gRPC" if self._is_cloud else f"self-hosted HTTP ({self.base_url})"
            logger.info("Using NVIDIA NIM ASR for transcription (%s)", mode)
            _startup_logged = True

        if not self.api_key:
            logger.warning("NVIDIA NIM STT configured but no API key set")

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResponse:
        """Transcribe audio using NVIDIA NIM ASR.

        Args:
            audio_file: Binary file object containing audio data.
            filename: Original filename (used to determine content type).
            language: Optional language code hint (e.g., 'en').

        Returns:
            TranscriptionResponse with transcript and metadata.
        """
        try:
            audio_bytes = audio_file.read()

            if self._is_cloud:
                transcript = await self._transcribe_cloud(audio_bytes, language)
            else:
                transcript = await self._transcribe_selfhosted(
                    audio_bytes, filename, language
                )

            return TranscriptionResponse(
                transcript=transcript,
                language=language,
                duration=None,
            )
        except Exception as e:
            logger.error("NVIDIA STT transcription failed: %s: %s", type(e).__name__, e)
            return TranscriptionResponse(transcript="", language=None, duration=None)

    async def _transcribe_cloud(
        self, audio_bytes: bytes, language: str | None
    ) -> str:
        """Transcribe via NVIDIA Cloud Riva ASR (gRPC)."""
        from app.services.grpc_stt_client import recognize_cloud

        language_code = self._to_bcp47(language) if language else "en-US"

        return await recognize_cloud(
            audio_bytes=audio_bytes,
            api_key=self.api_key or "",
            language_code=language_code,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _transcribe_selfhosted(
        self, audio_bytes: bytes, filename: str, language: str | None
    ) -> str:
        """Transcribe via self-hosted NIM HTTP endpoint (OpenAI-compatible)."""
        url = f"{self.base_url}/audio/transcriptions"

        content_type = self._get_content_type(filename)
        files = {"file": (filename, audio_bytes, content_type)}
        data: dict[str, str] = {"model": self.model}

        if language:
            data["language"] = language

        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=5.0)
        ) as client:
            response = await client.post(
                url, files=files, data=data, headers=headers
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")

    @staticmethod
    def _to_bcp47(language: str) -> str:
        """Convert a short language code to BCP-47 format if needed."""
        if "-" in language or "_" in language:
            return language.replace("_", "-")
        mapping = {
            "en": "en-US",
            "es": "es-US",
            "fr": "fr-FR",
            "de": "de-DE",
        }
        return mapping.get(language, f"{language}-{language.upper()}")

    @staticmethod
    def _get_content_type(filename: str) -> str:
        """Map filename extension to MIME type."""
        ext = filename.lower().split(".")[-1]
        mime_types = {
            "webm": "audio/webm",
            "opus": "audio/opus",
            "ogg": "audio/ogg",
            "mp3": "audio/mpeg",
            "mp4": "audio/mp4",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
            "flac": "audio/flac",
        }
        return mime_types.get(ext, "audio/webm")
