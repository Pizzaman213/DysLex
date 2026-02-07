"""Error profile endpoints — per-user adaptive error data."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserId, DbSession
from app.core.error_profile import error_profile_service
from app.models.envelope import success_response
from app.models.error_log import PersonalDictionaryAdd

router = APIRouter()


@router.get("/{user_id}")
async def get_profile(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get a user's full error profile."""
    _assert_own_profile(user_id, current_user)
    profile = await error_profile_service.get_full_profile(user_id, db)
    return success_response(profile.model_dump())


@router.get("/{user_id}/top-errors")
async def get_top_errors(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
    limit: int = 20,
) -> dict:
    """Return the top N most frequent errors for this user."""
    _assert_own_profile(user_id, current_user)
    top = await error_profile_service.get_top_errors(user_id, db, limit)
    return success_response({"top_errors": [e.model_dump() for e in top]})


@router.get("/{user_id}/confusion-pairs")
async def get_confusion_pairs(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return the user's confusion/homophone pairs."""
    _assert_own_profile(user_id, current_user)
    pairs = await error_profile_service.get_confusion_pairs(user_id, db)
    return success_response({"confusion_pairs": [p.model_dump() for p in pairs]})


@router.get("/{user_id}/error-types")
async def get_error_types(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return the user's error type breakdown."""
    _assert_own_profile(user_id, current_user)
    breakdown = await error_profile_service.get_error_type_breakdown(user_id, db)
    return success_response(breakdown.model_dump())


@router.get("/{user_id}/progress")
async def get_profile_progress(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
    weeks: int = 12,
) -> dict:
    """Weekly progress snapshots for the user."""
    _assert_own_profile(user_id, current_user)
    snapshots = await error_profile_service.get_progress(user_id, db, weeks)
    return success_response({"weekly_snapshots": [s.model_dump() for s in snapshots]})


@router.get("/{user_id}/dictionary")
async def get_dictionary(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get the user's personal dictionary."""
    _assert_own_profile(user_id, current_user)
    entries = await error_profile_service.get_personal_dictionary(user_id, db)
    return success_response({"dictionary": [e.model_dump() for e in entries]})


@router.post("/{user_id}/dictionary")
async def add_to_dictionary(
    user_id: str,
    body: PersonalDictionaryAdd,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Add a word to the user's personal dictionary."""
    _assert_own_profile(user_id, current_user)
    entry = await error_profile_service.add_to_dictionary(
        user_id, db, body.word, body.source
    )
    return success_response(entry.model_dump())


@router.delete("/{user_id}/dictionary/{word}")
async def remove_from_dictionary(
    user_id: str,
    word: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Remove a word from the user's personal dictionary."""
    _assert_own_profile(user_id, current_user)
    removed = await error_profile_service.remove_from_dictionary(user_id, db, word)
    return success_response({"removed": removed})


@router.get("/{user_id}/mastered")
async def get_mastered(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return patterns the user has mastered (not seen in 14+ days)."""
    _assert_own_profile(user_id, current_user)
    mastered = await error_profile_service.get_mastered_words(user_id, db)
    return success_response({"mastered": [m.model_dump() for m in mastered]})


@router.get("/{user_id}/llm-context")
async def get_llm_context(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return a pre-built LLM context blob for prompt injection."""
    _assert_own_profile(user_id, current_user)
    ctx = await error_profile_service.build_llm_context(user_id, db)
    return success_response(ctx.model_dump())


@router.get("/{user_id}/correction-dict")
async def get_correction_dict(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
    limit: int = 500,
) -> dict:
    """Return the user's misspelling -> correction map for the frontend ONNX model.

    Built automatically from the user's error profile (passive learning data).
    The frontend merges this on top of the base correction dictionary.
    """
    _assert_own_profile(user_id, current_user)
    patterns = await error_profile_service.get_top_errors(user_id, db, limit)
    correction_map: dict[str, str] = {}
    for p in patterns:
        entry = p.model_dump()
        misspelling = entry.get("misspelling", "").lower().strip()
        correction = entry.get("correction", "").lower().strip()
        if misspelling and correction and misspelling != correction:
            correction_map[misspelling] = correction
    return success_response({"correction_dict": correction_map, "count": len(correction_map)})


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _assert_own_profile(user_id: str, current_user: str) -> None:
    """Users may only access their own profile."""
    if user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile",
        )
