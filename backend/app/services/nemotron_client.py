"""Nemotron client for deep text analysis (Tier 2)."""

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.prompt_builder import build_correction_prompt, build_correction_prompt_v2
from app.models.correction import Correction
from app.models.error_log import LLMContext
from app.utils.json_parser import parse_json_from_llm_response

logger = logging.getLogger(__name__)


async def deep_analysis(
    text: str,
    user_id: str,
    context: str | None = None,
    profile: object | None = None,
    db: AsyncSession | None = None,
) -> list[Correction]:
    """Perform deep text analysis using Nemotron via NIM API (Tier 2)."""
    if not settings.nvidia_nim_api_key:
        return []

    # Build personalised prompt from the real error profile
    llm_context: LLMContext | None = None
    if db is not None:
        from app.core.error_profile import error_profile_service

        try:
            llm_context = await error_profile_service.build_llm_context(user_id, db)
        except Exception:
            logger.warning("Failed to load LLM context for user %s", user_id, exc_info=True)

    if llm_context is not None:
        prompt = build_correction_prompt_v2(text, llm_context, context)
    else:
        # Fallback to legacy prompt builder
        user_patterns: list[dict] = []
        confusion_pairs: list[dict] = []
        if profile is not None:
            user_patterns = getattr(profile, "top_patterns", [])
            confusion_pairs = getattr(profile, "confusion_pairs", [])
        prompt = build_correction_prompt(text, user_patterns, confusion_pairs, context)

    try:
        return await _call_nim_api(prompt)
    except Exception:
        logger.warning("Deep analysis NIM call failed after retries", exc_info=True)
        return []


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
async def _call_nim_api(prompt: str) -> list[Correction]:
    """Call NIM API with retry logic."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=30.0)) as client:
        response = await client.post(
            f"{settings.nvidia_nim_llm_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.nvidia_nim_llm_model,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        return parse_nemotron_response(response.json())


def parse_nemotron_response(response: dict) -> list[Correction]:
    """Parse Nemotron response into Correction objects."""
    try:
        content = response["choices"][0]["message"]["content"]

        corrections = parse_json_from_llm_response(
            content=content,
            model_class=Correction,
            is_array=True
        )

        return corrections

    except (KeyError, IndexError) as e:
        logger.error(f"Failed to extract content from response: {e}")
        return []
