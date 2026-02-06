"""Nemotron client for deep text analysis."""

import httpx

from app.config import settings
from app.core.prompt_builder import build_correction_prompt
from app.models.correction import Correction


async def deep_analysis(
    text: str,
    user_id: str,
    context: str | None = None,
) -> list[Correction]:
    """Perform deep text analysis using Nemotron via NIM API."""
    if not settings.nvidia_nim_api_key:
        return []

    # Get user's error profile for personalized prompts
    user_patterns: list[dict] = []  # Would fetch from database
    confusion_pairs: list[dict] = []  # Would fetch from database

    prompt = build_correction_prompt(text, user_patterns, confusion_pairs, context)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.nvidia_nim_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "nvidia/nemotron-4-340b-instruct",
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.2,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            # Parse response and convert to Correction objects
            return parse_nemotron_response(response.json())
        except httpx.HTTPError:
            return []


def parse_nemotron_response(response: dict) -> list[Correction]:
    """Parse Nemotron response into Correction objects."""
    corrections = []
    try:
        content = response["choices"][0]["message"]["content"]
        # Parse JSON from content
        # This would need proper JSON extraction logic
    except (KeyError, IndexError):
        pass
    return corrections
