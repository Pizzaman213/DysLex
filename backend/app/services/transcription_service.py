"""
Service for transcribing audio via a local faster-whisper server (OpenAI-compatible API).

Browser clients use Web Speech API directly and don't need this service.
This is used by desktop (Tauri) clients and as a backend fallback.
"""

import logging
from typing import BinaryIO

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.capture import TranscriptionResponse

logger = logging.getLogger(__name__)

_LOCALHOST_PREFIXES = ("http://localhost", "http://127.0.0.1", "http://0.0.0.0")


class TranscriptionService:
    """Handles audio transcription via a faster-whisper OpenAI-compatible endpoint."""

    def __init__(self) -> None:
        self.base_url = settings.transcription_url.rstrip("/")
        self.api_key = settings.nvidia_nim_api_key or None

        # Local faster-whisper doesn't need auth
        self._needs_auth = not self.base_url.startswith(_LOCALHOST_PREFIXES)

        if self._needs_auth and not self.api_key:
            logger.warning("Transcription URL is remote but no API key is configured")

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: str | None = None
    ) -> TranscriptionResponse:
        """
        Transcribe an audio file using faster-whisper (OpenAI-compatible API).

        Args:
            audio_file: Binary file object containing audio data
            filename: Original filename (used to determine content type)
            language: Optional language code hint (e.g., 'en')

        Returns:
            TranscriptionResponse with transcript and metadata

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/audio/transcriptions"

        content_type = self._get_content_type(filename)

        files = {
            "file": (filename, audio_file, content_type)
        }

        data: dict[str, str] = {
            "model": "faster-whisper",
        }

        if language:
            data["language"] = language

        headers: dict[str, str] = {}
        if self._needs_auth and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            return await self._call_api(url, files, data, headers)
        except Exception as e:
            logger.error(f"Transcription failed after retries: {e}")
            return TranscriptionResponse(transcript="", language=None, duration=None)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    )
    async def _call_api(
        self, url: str, files: dict, data: dict, headers: dict
    ) -> TranscriptionResponse:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=5.0)
        ) as client:
            response = await client.post(
                url, files=files, data=data, headers=headers
            )
            response.raise_for_status()
            result = response.json()
            return TranscriptionResponse(
                transcript=result.get("text", ""),
                language=result.get("language"),
                duration=result.get("duration"),
            )

    def _get_content_type(self, filename: str) -> str:
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
            "flac": "audio/flac"
        }

        return mime_types.get(ext, "audio/webm")


def _create_transcription_service() -> TranscriptionService:
    """Factory: select STT provider based on STT_PROVIDER setting."""
    if settings.stt_provider.lower() == "nvidia":
        from app.services.nvidia_stt_service import NvidiaTranscriptionService
        return NvidiaTranscriptionService()  # type: ignore[return-value]
    return TranscriptionService()


# Singleton instance
transcription_service = _create_transcription_service()
