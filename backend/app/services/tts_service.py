"""Text-to-speech service using MagpieTTS via NIM."""

import logging
import os
import time
import uuid
from pathlib import Path

import aiofiles
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


async def text_to_speech(text: str, voice: str = "default") -> str:
    """Convert text to speech using MagpieTTS."""
    if not settings.nvidia_nim_api_key:
        return ""

    try:
        response = await _call_tts_api(text, voice)
    except Exception:
        logger.warning("TTS call failed after retries", exc_info=True)
        return ""

    # Generate unique filename
    audio_id = str(uuid.uuid4())
    filename = f"{audio_id}.mp3"
    filepath = os.path.join(settings.tts_audio_dir, filename)

    # Ensure directory exists
    os.makedirs(settings.tts_audio_dir, exist_ok=True)

    # Save audio bytes to disk (async)
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(response.content)

    # Save metadata for cleanup (async)
    metadata_path = f"{filepath}.meta"
    async with aiofiles.open(metadata_path, 'w') as f:
        await f.write(str(time.time()))

    return f"{settings.tts_audio_base_url}/{filename}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
async def _call_tts_api(text: str, voice: str) -> httpx.Response:
    """Call TTS API with retry logic."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=30.0)) as client:
        response = await client.post(
            f"{settings.nvidia_nim_voice_url}/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "nvidia/magpietts",
                "input": text,
                "voice": voice,
                "response_format": "mp3",
            },
        )
        response.raise_for_status()
        return response


def cleanup_old_audio_files():
    """Remove TTS audio files older than cache TTL."""
    if not settings.tts_cleanup_enabled:
        return

    audio_dir = Path(settings.tts_audio_dir)
    if not audio_dir.exists():
        return

    current_time = time.time()
    ttl = settings.tts_cache_ttl

    for file in audio_dir.glob("*.mp3"):
        metadata_file = audio_dir / f"{file.name}.meta"

        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                created_time = float(f.read())

            if current_time - created_time > ttl:
                file.unlink()
                metadata_file.unlink()
                logger.info(f"Cleaned up old TTS file: {file.name}")


def get_available_voices() -> list[dict]:
    """Get list of available TTS voices."""
    return [
        {"id": "default", "name": "Default", "language": "en-US"},
        {"id": "slow", "name": "Slow Reader", "language": "en-US"},
    ]
