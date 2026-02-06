"""Text-to-speech service using MagpieTTS via NIM."""

import httpx

from app.config import settings


async def text_to_speech(text: str, voice: str = "default") -> str:
    """Convert text to speech using MagpieTTS."""
    if not settings.nvidia_nim_api_key:
        return ""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.nvidia_nim_base_url}/audio/speech",
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
                timeout=30.0,
            )
            response.raise_for_status()
            # In production, this would save audio and return URL
            return "/audio/generated.mp3"
        except httpx.HTTPError:
            return ""


def get_available_voices() -> list[dict]:
    """Get list of available TTS voices."""
    return [
        {"id": "default", "name": "Default", "language": "en-US"},
        {"id": "slow", "name": "Slow Reader", "language": "en-US"},
    ]
