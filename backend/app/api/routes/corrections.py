"""Text correction endpoints."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUserId, DbSession
from app.core.llm_orchestrator import get_corrections
from app.models.correction import CorrectionRequest, CorrectionResponse

router = APIRouter()


@router.post("", response_model=CorrectionResponse)
async def create_corrections(
    request: CorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> CorrectionResponse:
    """Get text corrections using the two-tier LLM system."""
    corrections = await get_corrections(
        text=request.text,
        user_id=user_id,
        context=request.context,
    )
    return CorrectionResponse(corrections=corrections)


@router.post("/quick")
async def quick_correction(
    request: CorrectionRequest,
    user_id: CurrentUserId,
) -> CorrectionResponse:
    """Quick correction using local model (no deep analysis)."""
    # This would use the Quick Correction Model
    return CorrectionResponse(corrections=[])
