"""Service for real-time streaming transcription."""

import logging
from io import BytesIO

from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)


class StreamingTranscriptionService:
    """Manages streaming transcription by accumulating audio chunks."""

    MAX_BUFFER_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self):
        self.chunk_buffer: bytes = b''
        self.buffer_threshold = 2.0  # seconds of audio before transcribing
        self.sample_rate = 48000
        self.bytes_per_second = 48000 * 2  # 16-bit audio = 2 bytes per sample

    async def process_chunk(self, audio_chunk: bytes) -> dict | None:
        """Process incoming audio chunk.

        Args:
            audio_chunk: Binary audio data

        Returns:
            Dict with transcript if threshold reached, None otherwise
        """
        # Guard against unbounded buffer growth
        if len(self.chunk_buffer) + len(audio_chunk) > self.MAX_BUFFER_BYTES:
            result = await self._transcribe_buffer()
            self.chunk_buffer = audio_chunk
            return result

        self.chunk_buffer += audio_chunk

        # Check if we have enough audio to transcribe
        buffer_duration = len(self.chunk_buffer) / self.bytes_per_second

        if buffer_duration >= self.buffer_threshold:
            return await self._transcribe_buffer()

        return None

    async def _transcribe_buffer(self) -> dict:
        """Send accumulated buffer to NIM for transcription.

        Returns:
            Dict with transcript text
        """
        if not self.chunk_buffer:
            return {"text": ""}

        try:
            # Convert buffer to file-like object
            audio_file = BytesIO(self.chunk_buffer)

            # Call TranscriptionService
            result = await transcription_service.transcribe_audio(
                audio_file=audio_file,
                filename="stream.webm"
            )

            # Clear buffer after transcription
            self.chunk_buffer = b''

            return {"text": result.transcript}

        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")
            self.chunk_buffer = b''  # Clear buffer on error
            return {"text": ""}

    async def finalize(self) -> dict:
        """Process any remaining buffered audio and return final transcript.

        Returns:
            Dict with final transcript text
        """
        if self.chunk_buffer:
            return await self._transcribe_buffer()
        return {"text": ""}
