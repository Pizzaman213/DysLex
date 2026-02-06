"""Two-tier LLM processing orchestrator."""

from app.models.correction import Correction
from app.services.nim_client import quick_correction
from app.services.nemotron_client import deep_analysis


async def get_corrections(
    text: str,
    user_id: str,
    context: str | None = None,
) -> list[Correction]:
    """
    Orchestrate two-tier LLM processing.

    Tier 1: Quick Correction Model (local ONNX or fast API call)
    - Common spelling errors
    - Simple grammar issues
    - Known confusion pairs for this user

    Tier 2: Deep Analysis (Nemotron via NIM)
    - Complex grammar
    - Context-dependent corrections
    - Nuanced word choice
    """
    corrections = []

    # Tier 1: Quick corrections
    quick_results = await quick_correction(text, user_id)
    corrections.extend(quick_results)

    # Tier 2: Deep analysis for remaining issues
    if needs_deep_analysis(text, quick_results):
        deep_results = await deep_analysis(text, user_id, context)
        corrections.extend(deep_results)

    # Deduplicate and prioritize
    return deduplicate_corrections(corrections)


def needs_deep_analysis(text: str, quick_results: list[Correction]) -> bool:
    """Determine if text needs deep analysis."""
    # Heuristics:
    # - Long sentences
    # - Complex grammar patterns
    # - Remaining uncorrected errors
    word_count = len(text.split())
    return word_count > 20 or len(quick_results) == 0


def deduplicate_corrections(corrections: list[Correction]) -> list[Correction]:
    """Remove duplicate corrections, keeping highest confidence."""
    seen_positions = {}
    for correction in corrections:
        key = (correction.start, correction.end)
        if key not in seen_positions or correction.confidence > seen_positions[key].confidence:
            seen_positions[key] = correction
    return list(seen_positions.values())
