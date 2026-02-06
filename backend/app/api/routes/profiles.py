"""Error profile endpoints."""

from fastapi import APIRouter

from app.api.dependencies import CurrentUserId, DbSession
from app.core.error_profile import get_user_profile, update_user_profile
from app.models.error_log import ErrorProfile, ErrorProfileUpdate

router = APIRouter()


@router.get("/me", response_model=ErrorProfile)
async def get_my_profile(
    user_id: CurrentUserId,
    db: DbSession,
) -> ErrorProfile:
    """Get the current user's error profile."""
    return await get_user_profile(user_id, db)


@router.patch("/me", response_model=ErrorProfile)
async def update_my_profile(
    update: ErrorProfileUpdate,
    user_id: CurrentUserId,
    db: DbSession,
) -> ErrorProfile:
    """Update the current user's error profile."""
    return await update_user_profile(user_id, update, db)


@router.get("/me/patterns")
async def get_my_patterns(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get the user's learned error patterns."""
    profile = await get_user_profile(user_id, db)
    return {"patterns": profile.top_patterns}


@router.get("/me/confusion-pairs")
async def get_my_confusion_pairs(
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get the user's common confusion pairs."""
    profile = await get_user_profile(user_id, db)
    return {"confusion_pairs": profile.confusion_pairs}
