"""Text-to-speech service using MagpieTTS via NVIDIA Riva TTS NIM.

Supports two modes:
  - Cloud API (integrate.api.nvidia.com): Uses gRPC via grpc_tts_client
  - Self-hosted Riva NIM (e.g. localhost:9000): Uses HTTP /audio/synthesize
"""

import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

# Cloud API hostnames that require gRPC instead of HTTP
_CLOUD_HOSTS = {"integrate.api.nvidia.com", "api.nvidia.com", "api.nvcf.nvidia.com"}

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


def _is_cloud_url(voice_url: str) -> bool:
    """Check if the voice URL points at NVIDIA's cloud API (requires gRPC)."""
    try:
        from urllib.parse import urlparse
        host = urlparse(voice_url).hostname or ""
        return host in _CLOUD_HOSTS
    except Exception:
        return False


async def _generate_and_cache(text: str, voice: str, content_hash: str) -> str:
    """Call NVIDIA Riva TTS API, save as {hash}.wav, return audio URL.

    If the file already exists on disk (cache hit), skips the API call.
    Auto-detects cloud vs self-hosted and uses the appropriate protocol.
    """
    filename = f"{content_hash}.wav"
    filepath = os.path.join(settings.tts_audio_dir, filename)

    # Cache hit — file already exists
    if os.path.exists(filepath):
        logger.debug("TTS cache hit: %s", content_hash[:12])
        return f"{settings.tts_audio_base_url}/{filename}"

    # Cache miss — call API
    is_cloud = _is_cloud_url(settings.nvidia_nim_voice_url)
    logger.info("TTS cache miss for %s — using %s path", content_hash[:12], "cloud gRPC" if is_cloud else "self-hosted HTTP")
    try:
        if is_cloud:
            audio_bytes = await _call_tts_api_cloud(text, voice)
        else:
            response = await _call_tts_api_selfhosted(text, voice)
            audio_bytes = response.content
    except TtsUnavailableError as e:
        logger.warning("TTS unavailable: %s", e)
        return ""
    except Exception as e:
        logger.error("TTS call failed: %s: %s", type(e).__name__, e, exc_info=True)
        return ""

    os.makedirs(settings.tts_audio_dir, exist_ok=True)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(audio_bytes)

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
_cloud_tts_logged = False


async def _call_tts_api_cloud(text: str, voice: str) -> bytes:
    """Call NVIDIA Cloud Riva TTS via gRPC.

    The NVIDIA cloud API (integrate.api.nvidia.com) only supports gRPC
    for TTS — the HTTP endpoint does not exist. This function uses the
    grpc_tts_client module to make the call.
    """
    global _cloud_tts_logged, _tts_unavailable_logged
    from app.services.grpc_tts_client import synthesize_cloud

    if not _cloud_tts_logged:
        logger.info("Using NVIDIA Cloud gRPC for TTS (Magpie-TTS-Multilingual)")
        _cloud_tts_logged = True

    try:
        return await synthesize_cloud(
            text=text,
            voice=voice,
            api_key=settings.nvidia_nim_api_key,
        )
    except Exception as e:
        error_str = str(e)
        # Check for authentication or function-not-found errors
        if "UNAUTHENTICATED" in error_str or "PERMISSION_DENIED" in error_str:
            if not _tts_unavailable_logged:
                logger.warning(
                    "TTS gRPC auth failed — check NVIDIA_NIM_API_KEY. "
                    "Error: %s",
                    error_str[:200],
                )
                _tts_unavailable_logged = True
            raise TtsUnavailableError("Cloud gRPC auth failed")
        raise


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=1, max=5),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
async def _call_tts_api_selfhosted(text: str, voice: str) -> httpx.Response:
    """Call self-hosted Riva TTS NIM via HTTP.

    Uses the Riva TTS /v1/audio/synthesize endpoint with multipart form data.
    For self-hosted Riva TTS NIM containers (e.g. http://localhost:9000/v1).
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
                    "Set NVIDIA_NIM_VOICE_URL to a self-hosted Riva TTS NIM "
                    "(e.g. http://localhost:9000/v1).",
                    url,
                )
                _tts_unavailable_logged = True
            raise TtsUnavailableError(url)
        response.raise_for_status()
        return response


class TtsUnavailableError(Exception):
    """Raised when the TTS endpoint is not available (e.g. 404)."""


def cleanup_old_audio_files() -> None:
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
            with open(metadata_file) as f:
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
