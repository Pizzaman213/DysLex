"""Two-tier LLM processing orchestrator with confidence-based routing."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.circuit_breaker import CircuitBreakerOpen
from app.core.error_profile import get_user_profile
from app.models.correction import Correction
from app.services.nemotron_client import deep_analysis
from app.services.nim_client import quick_correction

logger = logging.getLogger(__name__)


async def quick_only(
    text: str,
    user_id: str,
    db: AsyncSession,
) -> list[Correction]:
    """Run Tier 1 (quick) corrections only."""
    profile = await _safe_get_profile(user_id, db)
    results = await quick_correction(text, user_id, profile)
    return results


async def deep_only(
    text: str,
    user_id: str,
    context: str | None = None,
    db: AsyncSession | None = None,
    *,
    raise_on_error: bool = False,
) -> list[Correction]:
    """Run Tier 2 (deep analysis) corrections only."""
    profile = await _safe_get_profile(user_id, db)
    results = await deep_analysis(
        text, user_id, context, profile, db=db, raise_on_error=raise_on_error,
    )
    for r in results:
        r.tier = "deep"
    return results


async def auto_route(
    text: str,
    user_id: str,
    context: str | None = None,
    db: AsyncSession | None = None,
) -> list[Correction]:
    """Primary endpoint — confidence-based two-tier routing.

    1. Load user Error Profile
    2. Send text + profile to Quick Correction (Tier 1)
    3. For each correction: if confidence >= threshold -> keep; else flag for Tier 2
    4. If flagged tokens exist -> send to Deep Analysis with profile context
    5. Merge results (deep overrides quick for overlapping positions)
    6. Return merged results with tier metadata
    """
    profile = await _safe_get_profile(user_id, db)

    # Tier 1 — quick corrections
    quick_results = await quick_correction(text, user_id, profile)

    threshold = settings.confidence_threshold
    confident = [c for c in quick_results if c.confidence >= threshold]
    flagged = [c for c in quick_results if c.confidence < threshold]

    if not flagged and not _needs_deep_analysis(text, quick_results):
        return confident

    # Tier 2 — deep analysis for flagged/uncertain tokens
    try:
        deep_results = await deep_analysis(text, user_id, context, profile, db=db)
    except CircuitBreakerOpen:
        logger.warning("NIM circuit breaker OPEN — returning Tier 1 results only (degraded mode)")
        return confident

    for r in deep_results:
        r.tier = "deep"

    # Merge: deep overrides quick at overlapping positions
    merged = _merge_corrections(confident, deep_results)
    return merged


async def document_review(
    text: str,
    user_id: str,
    context: str | None = None,
    db: AsyncSession | None = None,
) -> list[Correction]:
    """Full-document deep review — always uses Tier 2."""
    return await deep_only(text, user_id, context, db, raise_on_error=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _safe_get_profile(
    user_id: str, db: AsyncSession | None
) -> object | None:
    """Load user profile, returning None on any failure."""
    if db is None:
        return None
    try:
        return await get_user_profile(user_id, db)
    except Exception:
        logger.warning("Failed to load profile for user %s — continuing without it", user_id, exc_info=True)
        return None


def _needs_deep_analysis(text: str, quick_results: list[Correction]) -> bool:
    """Heuristic: should we also run Tier 2?"""
    word_count = len(text.split())
    return word_count > 20 or len(quick_results) == 0


def _merge_corrections(
    confident: list[Correction],
    deep: list[Correction],
) -> list[Correction]:
    """Merge quick (confident) and deep results; deep wins on overlap."""
    by_pos: dict[tuple[int, int], Correction] = {}
    no_pos: list[Correction] = []
    for c in confident:
        if c.position is None:
            no_pos.append(c)
            continue
        key = (c.position.start, c.position.end)
        by_pos[key] = c
    for c in deep:
        if c.position is None:
            no_pos.append(c)
            continue
        key = (c.position.start, c.position.end)
        # Deep always overrides quick at same position
        by_pos[key] = c
    return list(by_pos.values()) + no_pos
