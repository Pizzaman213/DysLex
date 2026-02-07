"""Text-to-speech service using MagpieTTS via NVIDIA Riva TTS NIM."""

import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path

import aiofiles
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

# Map friendly voice IDs to NVIDIA Riva voice names
_VOICE_MAP: dict[str, str] = {
    "default": "Magpie-Multilingual.EN-US.Aria",
    "slow": "Magpie-Multilingual.EN-US.Aria",
    "aria": "Magpie-Multilingual.EN-US.Aria",
    "diego": "Magpie-Multilingual.ES-US.Diego",
    "louise": "Magpie-Multilingual.FR-FR.Louise",
}


def _resolve_voice(voice: str) -> str:
    """Map a friendly voice ID to the NVIDIA Riva voice name."""
    return _VOICE_MAP.get(voice, voice)


def _content_hash(text: str, voice: str) -> str:
    """Generate a deterministic SHA-256 hash for a (voice, text) pair."""
    key = f"{voice}:{text.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


async def _generate_and_cache(text: str, voice: str, content_hash: str) -> str:
    """Call NVIDIA Riva TTS API, save as {hash}.wav, return audio URL.

    If the file already exists on disk (cache hit), skips the API call.
    """
    filename = f"{content_hash}.wav"
    filepath = os.path.join(settings.tts_audio_dir, filename)

    # Cache hit — file already exists
    if os.path.exists(filepath):
        logger.debug("TTS cache hit: %s", content_hash[:12])
        return f"{settings.tts_audio_base_url}/{filename}"

    # Cache miss — call API
    try:
        response = await _call_tts_api(text, voice)
    except TtsUnavailableError:
        return ""
    except Exception:
        logger.warning("TTS call failed after retries", exc_info=True)
        return ""

    os.makedirs(settings.tts_audio_dir, exist_ok=True)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(response.content)

    # Metadata for cleanup
    async with aiofiles.open(f"{filepath}.meta", "w") as f:
        await f.write(str(time.time()))

    return f"{settings.tts_audio_base_url}/{filename}"


async def text_to_speech(text: str, voice: str = "default") -> str:
    """Convert text to speech using MagpieTTS (content-addressed caching)."""
    if not settings.nvidia_nim_api_key:
        return ""

    riva_voice = _resolve_voice(voice)
    h = _content_hash(text, riva_voice)
    return await _generate_and_cache(text, riva_voice, h)


async def batch_text_to_speech(
    sentences: list[dict],
    voice: str = "default",
) -> list[dict]:
    """Synthesize multiple sentences, reusing cached files.

    Parameters
    ----------
    sentences : list of {"index": int, "text": str}
    voice : TTS voice id

    Returns
    -------
    list of {"index": int, "audio_url": str, "cached": bool}
    """
    if not settings.nvidia_nim_api_key:
        return [{"index": s["index"], "audio_url": "", "cached": False} for s in sentences]

    riva_voice = _resolve_voice(voice)
    results: list[dict] = []
    uncached: list[tuple[int, str, str]] = []  # (list_index, text, hash)

    # Partition into cached / uncached
    for i, s in enumerate(sentences):
        h = _content_hash(s["text"], riva_voice)
        filename = f"{h}.wav"
        filepath = os.path.join(settings.tts_audio_dir, filename)

        if os.path.exists(filepath):
            results.append({
                "index": s["index"],
                "audio_url": f"{settings.tts_audio_base_url}/{filename}",
                "cached": True,
            })
        else:
            uncached.append((i, s["text"], h))
            # Placeholder — will be filled after API calls
            results.append({
                "index": s["index"],
                "audio_url": "",
                "cached": False,
            })

    if uncached:
        os.makedirs(settings.tts_audio_dir, exist_ok=True)

        async def _synth(list_idx: int, text: str, content_hash: str) -> None:
            url = await _generate_and_cache(text, riva_voice, content_hash)
            results[list_idx]["audio_url"] = url
            results[list_idx]["cached"] = False

        await asyncio.gather(*[_synth(li, t, h) for li, t, h in uncached])

    return results


# Track whether we've already logged the TTS unavailable warning
_tts_unavailable_logged = False


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=1, max=5),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
async def _call_tts_api(text: str, voice: str) -> httpx.Response:
    """Call NVIDIA Riva TTS HTTP API with retry logic.

    Uses the Riva TTS /v1/audio/synthesize endpoint with multipart form data.
    Requires a self-hosted Riva TTS NIM container — the NVIDIA cloud API
    (integrate.api.nvidia.com) does not expose HTTP TTS endpoints.

    Set NVIDIA_NIM_VOICE_URL to point at your Riva TTS instance
    (e.g. http://localhost:9000/v1).
    """
    global _tts_unavailable_logged
    url = f"{settings.nvidia_nim_voice_url}/audio/synthesize"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                "Accept": "audio/wav",
            },
            data={
                "text": text,
                "voice": voice,
                "language": "en-US",
            },
        )
        if response.status_code == 404:
            if not _tts_unavailable_logged:
                logger.warning(
                    "TTS endpoint returned 404 at %s. "
                    "NVIDIA cloud API does not support HTTP TTS — "
                    "set NVIDIA_NIM_VOICE_URL to a self-hosted Riva TTS NIM "
                    "(e.g. http://localhost:9000/v1). "
                    "TTS will be disabled until a valid endpoint is configured.",
                    url,
                )
                _tts_unavailable_logged = True
            raise TtsUnavailableError(url)
        response.raise_for_status()
        return response


class TtsUnavailableError(Exception):
    """Raised when the TTS endpoint is not available (e.g. 404)."""


def cleanup_old_audio_files():
    """Remove TTS audio files older than cache TTL."""
    if not settings.tts_cleanup_enabled:
        return

    audio_dir = Path(settings.tts_audio_dir)
    if not audio_dir.exists():
        return

    current_time = time.time()
    ttl = settings.tts_cache_ttl

    for file in audio_dir.glob("*.wav"):
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
        {"id": "default", "name": "Aria (English)", "language": "en-US"},
        {"id": "aria", "name": "Aria (English)", "language": "en-US"},
        {"id": "diego", "name": "Diego (Spanish)", "language": "es-US"},
        {"id": "louise", "name": "Louise (French)", "language": "fr-FR"},
    ]
