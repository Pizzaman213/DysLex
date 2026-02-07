"""Adaptive learning — control and stats endpoints."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUserId, DbSession
from app.core.adaptive_loop import compute_learning_signal
from app.models.envelope import success_response
from app.services.scheduler import get_scheduler, trigger_job_now

router = APIRouter()


@router.post("/trigger-retrain")
async def trigger_retrain(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Manually trigger a retrain of the user's Quick Correction model.

    Triggers the nightly retraining job immediately.
    Full ML pipeline integration depends on Module 3 completion.
    """
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not running")

    # Trigger the retraining job immediately
    success = trigger_job_now("trigger_model_retraining")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger retraining job")

    return success_response({
        "retrain_requested": True,
        "user_id": user_id,
        "status": "Job triggered - check logs for progress"
    })


@router.get("/stats/{user_id}")
async def learning_stats(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return adaptive learning statistics for a user."""
    signal = await compute_learning_signal(user_id, db=db)
    return success_response({
        "signals_captured": len(signal.get("patterns_reinforced", [])),
        "patterns_updated": len(signal.get("patterns_weakened", [])),
        "last_retrain": None,
        "overall_trend": signal.get("overall_trend", "stable"),
    })
