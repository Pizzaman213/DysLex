"""User management endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserId, DbSession, hash_password
from app.db.models import User as UserORM
from app.db.repositories.error_log_repo import get_error_logs_by_user
from app.db.repositories.personal_dictionary_repo import get_dictionary
from app.db.repositories.progress_snapshot_repo import get_snapshots
from app.db.repositories.settings_repo import get_or_create_settings
from app.db.repositories.settings_repo import update_settings as update_settings_repo
from app.db.repositories.user_confusion_pair_repo import get_pairs_for_user
from app.db.repositories.user_error_pattern_repo import get_top_patterns
from app.db.repositories.user_repo import create_user, delete_user, get_user_by_id
from app.models.envelope import success_response
from app.models.user import User, UserCreate, UserSettings, UserSettingsUpdate

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserCreate,
    db: DbSession,
) -> dict:
    """Create a new user (admin endpoint)."""
    user = UserORM(
        id=str(uuid.uuid4()),
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
    )
    user = await create_user(db, user)
    return success_response(
        User(id=user.id, email=user.email, name=user.name).model_dump(),
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get user info and settings."""
    _assert_own_user(user_id, current_user)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = await get_or_create_settings(db, user_id)
    return success_response({
        "user": User(id=user.id, email=user.email, name=user.name).model_dump(),
        "settings": UserSettings.model_validate(settings).model_dump(by_alias=True),
    })


@router.get("/{user_id}/settings")
async def get_settings(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Get user settings only."""
    _assert_own_user(user_id, current_user)
    settings = await get_or_create_settings(db, user_id)
    return success_response(UserSettings.model_validate(settings).model_dump(by_alias=True))


@router.put("/{user_id}/settings")
async def update_settings(
    user_id: str,
    body: UserSettingsUpdate,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Update user settings (font, theme, etc.)."""
    _assert_own_user(user_id, current_user)

    # Get or create settings first
    await get_or_create_settings(db, user_id)

    # Update with partial data
    updates = body.model_dump(exclude_unset=True)
    settings = await update_settings_repo(db, user_id, updates)

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    return success_response(UserSettings.model_validate(settings).model_dump(by_alias=True))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> None:
    """GDPR cascade delete — removes user and all associated data."""
    _assert_own_user(user_id, current_user)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await delete_user(db, user)
    await db.commit()  # Ensure transaction is committed


@router.get("/{user_id}/export")
async def export_user_data(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Export all user data as JSON (GDPR data portability).

    Returns complete user data across all tables for GDPR compliance.
    """
    _assert_own_user(user_id, current_user)
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query all user data across all tables
    settings = await get_or_create_settings(db, user_id)
    error_logs = await get_error_logs_by_user(db, user_id, limit=10000)
    error_patterns = await get_top_patterns(db, user_id, limit=1000)
    confusion_pairs = await get_pairs_for_user(db, user_id, limit=1000)
    personal_dict = await get_dictionary(db, user_id)
    snapshots = await get_snapshots(db, user_id, weeks=104)  # 2 years

    # Build complete export with all 7 sections
    export_data = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "settings": {
            "language": settings.language,
            "mind_map_enabled": settings.mind_map_enabled,
            "draft_mode_enabled": settings.draft_mode_enabled,
            "polish_mode_enabled": settings.polish_mode_enabled,
            "passive_learning": settings.passive_learning,
            "ai_coaching": settings.ai_coaching,
            "inline_corrections": settings.inline_corrections,
            "progress_tracking": settings.progress_tracking,
            "read_aloud": settings.read_aloud,
            "theme": settings.theme,
            "font": settings.font,
            "page_type": settings.page_type,
            "view_mode": settings.view_mode,
            "zoom": settings.zoom,
            "show_zoom": settings.show_zoom,
            "page_numbers": settings.page_numbers,
            "font_size": settings.font_size,
            "line_spacing": settings.line_spacing,
            "letter_spacing": settings.letter_spacing,
            "voice_enabled": settings.voice_enabled,
            "auto_correct": settings.auto_correct,
            "focus_mode": settings.focus_mode,
            "tts_speed": settings.tts_speed,
            "correction_aggressiveness": settings.correction_aggressiveness,
            "anonymized_data_collection": settings.anonymized_data_collection,
            "cloud_sync": settings.cloud_sync,
            "developer_mode": settings.developer_mode,
        },
        "error_logs": [
            {
                "original": log.original_text,
                "corrected": log.corrected_text,
                "error_type": log.error_type,
                "context": log.context,
                "confidence": log.confidence,
                "source": log.source,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
            }
            for log in error_logs
        ],
        "error_patterns": [
            {
                "misspelling": p.misspelling,
                "correction": p.correction,
                "error_type": p.error_type,
                "frequency": p.frequency,
                "language_code": p.language_code,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
                "improving": p.improving,
            }
            for p in error_patterns
        ],
        "confusion_pairs": [
            {
                "word_a": c.word_a,
                "word_b": c.word_b,
                "confusion_count": c.confusion_count,
                "last_confused_at": c.last_confused_at.isoformat() if c.last_confused_at else None,
            }
            for c in confusion_pairs
        ],
        "personal_dictionary": [entry.word for entry in personal_dict],
        "progress_snapshots": [
            {
                "week_start": s.week_start.isoformat() if s.week_start else None,
                "total_words_written": s.total_words_written,
                "total_corrections": s.total_corrections,
                "accuracy_score": s.accuracy_score,
                "error_type_breakdown": s.error_type_breakdown,
                "top_errors": s.top_errors,
                "patterns_mastered": s.patterns_mastered,
                "new_patterns_detected": s.new_patterns_detected,
            }
            for s in snapshots
        ],
        "exported_at": datetime.utcnow().isoformat(),
    }

    return success_response(export_data)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _assert_own_user(user_id: str, current_user: str) -> None:
    if user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own account",
        )
