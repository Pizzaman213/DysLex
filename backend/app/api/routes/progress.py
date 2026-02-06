"""Progress tracking endpoints."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUserId, DbSession
from app.models.progress import ProgressStats

router = APIRouter()


@router.get("", response_model=ProgressStats)
async def get_progress(
    user_id: CurrentUserId,
    db: DbSession,
) -> ProgressStats:
    """Get user's progress statistics."""
    # Placeholder - would query from database
    return ProgressStats(
        overall_score=65,
        words_written=12500,
        corrections_accepted=342,
        patterns_mastered=8,
        streak_days=5,
        achievements=[],
    )


@router.get("/history")
async def get_progress_history(
    user_id: CurrentUserId,
    db: DbSession,
    days: int = 30,
) -> dict:
    """Get historical progress data."""
    return {"history": [], "period_days": days}


@router.get("/achievements")
async def get_achievements(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get user's achievements."""
    return {"achievements": []}
