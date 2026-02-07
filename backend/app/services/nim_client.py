"""NVIDIA NIM API client for quick corrections (Tier 1).

Now uses local ONNX model via QuickCorrectionService for fast corrections.
Falls back gracefully if model is not available.
"""

import logging

from app.models.correction import Correction

logger = logging.getLogger(__name__)

# Import QuickCorrectionService
_quick_service = None


def _get_quick_service():
    """Get or initialize Quick Correction Service."""
    global _quick_service
    if _quick_service is None:
        from app.services.quick_correction_service import get_quick_correction_service

        _quick_service = get_quick_correction_service()
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
            corrections = await service.correct(text, user_id)
            logger.debug(f"Quick correction found {len(corrections)} errors")
            return corrections
        except Exception as e:
            logger.error(f"Quick correction failed: {e}", exc_info=True)

    # Fallback: return empty list (will trigger Tier 2)
    logger.debug("Quick correction not available, falling back to Tier 2")
    return []
