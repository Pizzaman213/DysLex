"""Progress tracking endpoints."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUserId, DbSession
from app.core.error_profile import error_profile_service
from app.db.repositories import progress_repo
from app.models.envelope import success_response
from app.services.redis_client import cache_get, cache_set
from app.models.progress import (
    ErrorFrequencyWeek,
    ErrorTypeBreakdown,
    ErrorTypeImprovement,
    MasteredWord,
    ProgressDashboardResponse,
    TopError,
    TotalStats,
    WritingStreak,
)

router = APIRouter()


@router.get("")
async def get_progress(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get user's progress statistics."""
    profile = await error_profile_service.get_full_profile(user_id, db)
    improvement = await error_profile_service.detect_improvement(user_id, db)
    return success_response({
        "overall_score": profile.overall_score,
        "patterns_mastered": profile.patterns_mastered,
        "total_patterns": profile.total_patterns,
        "trend": improvement["trend"],
        "recent_errors": improvement["recent_errors"],
        "prior_errors": improvement["prior_errors"],
    })


@router.get("/history")
async def get_progress_history(
    user_id: CurrentUserId,
    db: DbSession,
    weeks: int = 12,
) -> dict:
    """Get historical progress data (weekly snapshots)."""
    snapshots = await error_profile_service.get_progress(user_id, db, weeks)
    return success_response({
        "history": [s.model_dump() for s in snapshots],
        "period_weeks": weeks,
    })


@router.get("/achievements")
async def get_achievements(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get user's achievements (mastered patterns)."""
    mastered = await error_profile_service.get_mastered_words(user_id, db)
    return success_response({
        "achievements": [
            {
                "word": m.misspelling,
                "correction": m.correction,
                "mastered": True,
                "last_seen": m.last_seen.isoformat(),
            }
            for m in mastered
        ]
    })


@router.post("/snapshot")
async def generate_snapshot(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Generate/update the current week's progress snapshot."""
    snapshot = await error_profile_service.generate_weekly_snapshot(user_id, db)
    return success_response(snapshot.model_dump())


@router.get("/dashboard")
async def get_dashboard(
    user_id: CurrentUserId,
    db: DbSession,
    weeks: int = 12,
) -> dict:
    """Get complete progress dashboard data."""
    cache_key = f"dashboard:{user_id}:{weeks}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # Fetch all dashboard data
    error_frequency = await progress_repo.get_error_frequency_by_week(db, user_id, weeks)
    error_breakdown = await progress_repo.get_error_breakdown_by_type(db, user_id, weeks)
    top_errors = await progress_repo.get_top_errors(db, user_id, limit=10, weeks=weeks)
    mastered_words = await progress_repo.get_mastered_words(db, user_id, weeks=4)
    writing_streak = await progress_repo.get_writing_streak(db, user_id)
    total_stats = await progress_repo.get_total_stats(db, user_id)
    improvements = await progress_repo.get_improvement_by_error_type(db, user_id, weeks)

    # Build response
    dashboard = ProgressDashboardResponse(
        error_frequency=[ErrorFrequencyWeek(**item) for item in error_frequency],
        error_breakdown=[ErrorTypeBreakdown(**item) for item in error_breakdown],
        top_errors=[TopError(**item) for item in top_errors],
        mastered_words=[MasteredWord(**item) for item in mastered_words],
        writing_streak=WritingStreak(**writing_streak),
        total_stats=TotalStats(**total_stats),
        improvements=[ErrorTypeImprovement(**item) for item in improvements],
    )

    response = success_response(dashboard.model_dump())
    await cache_set(cache_key, response, ttl_seconds=300)
    return response
