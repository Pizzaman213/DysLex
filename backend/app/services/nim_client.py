"""NVIDIA NIM API client for quick corrections (Tier 1).

Now uses local ONNX model via QuickCorrectionService for fast corrections.
Falls back gracefully if model is not available.
"""

import logging

from app.models.correction import Correction

logger = logging.getLogger(__name__)

# Import QuickCorrectionService — _UNAVAILABLE sentinel prevents retrying broken imports.
_quick_service: object | None = None
_UNAVAILABLE = object()


def _get_quick_service() -> object | None:
    """Get or initialize Quick Correction Service."""
    global _quick_service
    if _quick_service is _UNAVAILABLE:
        return None
    if _quick_service is None:
        try:
            from app.services.quick_correction_service import get_quick_correction_service

            _quick_service = get_quick_correction_service()
        except Exception as e:
            logger.warning("Quick correction service unavailable: %s", e)
            _quick_service = _UNAVAILABLE
            return None
    return _quick_service


async def quick_correction(
    text: str,
    user_id: str,
    profile: object | None = None,
) -> list[Correction]:
    """Get quick corrections using local ONNX model (Tier 1).

    Returns an empty list when the model is not available or inference fails.
    The system degrades gracefully to Tier 2 (deep analysis) in these cases.

    Args:
        text: Text to correct
        user_id: User ID for personalization
        profile: Optional user error profile (for future use)

    Returns:
        List of corrections with confidence scores
    """
    # Try local ONNX model first
    service = _get_quick_service()

    if service is not None:
        try:
            corrections: list[Correction] = await service.correct(text, user_id)  # type: ignore[attr-defined]
            logger.debug(f"Quick correction found {len(corrections)} errors")
            return corrections
        except Exception as e:
            logger.error(f"Quick correction failed: {e}", exc_info=True)

    # Fallback: return empty list (will trigger Tier 2)
    logger.debug("Quick correction not available, falling back to Tier 2")
    return []
