"""NVIDIA NIM API client for quick corrections."""

import httpx

from app.config import settings
from app.models.correction import Correction


async def quick_correction(text: str, user_id: str) -> list[Correction]:
    """Get quick corrections using NVIDIA NIM API."""
    if not settings.nvidia_nim_api_key:
        return []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.nvidia_nim_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "nvidia/nemotron-mini-4b-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a spelling and grammar correction assistant. Return corrections in JSON format.",
                        },
                        {
                            "role": "user",
                            "content": f"Find spelling and grammar errors in: {text}",
                        },
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            # Parse response and convert to Correction objects
            return []
        except httpx.HTTPError:
            return []
