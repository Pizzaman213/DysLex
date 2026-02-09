"""Integration tests for GDPR compliance features."""

import uuid

import pytest
import pytest_asyncio
from datetime import date, datetime

from app.db.models import (
    User,
    UserSettings,
    ErrorLog,
    UserErrorPattern,
    UserConfusionPair,
    PersonalDictionary,
    ProgressSnapshot,
)
from app.db.repositories import (
    user_repo,
    settings_repo,
    error_log_repo,
    user_error_pattern_repo,
    user_confusion_pair_repo,
    personal_dictionary_repo,
    progress_snapshot_repo,
)


@pytest_asyncio.fixture
async def test_user_with_data(db):
    """Create a test user with data in all tables."""
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user)

    # Create settings
    await settings_repo.create_default_settings(db, user.id)

    # Create error logs
    await error_log_repo.create_error_log(
        db,
        user_id=user.id,
        original_text="teh",
        corrected_text="the",
        error_type="spelling",
        source="passive",
    )

    # Create error pattern
    await user_error_pattern_repo.upsert_pattern(
        db,
        user_id=user.id,
        misspelling="teh",
        correction="the",
        error_type="spelling",
    )

    # Create confusion pair
    await user_confusion_pair_repo.upsert_confusion_pair(
        db,
        user_id=user.id,
        word_a="their",
        word_b="there",
    )

    # Create personal dictionary entry
    await personal_dictionary_repo.add_word(
        db,
        user_id=user.id,
        word="dyslex",
        source="manual",
    )

    # Create progress snapshot
    await progress_snapshot_repo.upsert_snapshot(
        db,
        user_id=user.id,
        week_start=date(2026, 2, 3),  # Monday
        total_words_written=500,
        total_corrections=25,
        accuracy_score=95.0,
    )

    await db.commit()
    return user


@pytest.mark.asyncio
async def test_export_all_user_data_structure(test_user_with_data, db):
    """Export should return complete user data with all 7 sections."""
    user = test_user_with_data

    # Get settings
    settings = await settings_repo.get_or_create_settings(db, user.id)

    # Get all data
    error_logs = await error_log_repo.get_error_logs_by_user(db, user.id, limit=10000)
    error_patterns = await user_error_pattern_repo.get_top_patterns(db, user.id, limit=1000)
    confusion_pairs = await user_confusion_pair_repo.get_pairs_for_user(db, user.id, limit=1000)
    personal_dict = await personal_dictionary_repo.get_dictionary(db, user.id)
    snapshots = await progress_snapshot_repo.get_snapshots(db, user.id, weeks=104)

    # Build export data structure (mimicking the endpoint)
    export_data = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "settings": {
            "theme": settings.theme,
            "font": settings.font,
        },
        "error_logs": [
            {
                "original": log.original_text,
                "corrected": log.corrected_text,
                "error_type": log.error_type,
            }
            for log in error_logs
        ],
        "error_patterns": [
            {
                "misspelling": p.misspelling,
                "correction": p.correction,
                "frequency": p.frequency,
            }
            for p in error_patterns
        ],
        "confusion_pairs": [
            {
                "word_a": c.word_a,
                "word_b": c.word_b,
                "confusion_count": c.confusion_count,
            }
            for c in confusion_pairs
        ],
        "personal_dictionary": [entry.word for entry in personal_dict],
        "progress_snapshots": [
            {
                "week_start": s.week_start.isoformat() if s.week_start else None,
                "total_words_written": s.total_words_written,
            }
            for s in snapshots
        ],
    }

    # Verify all 7 sections are present and populated
    assert "user" in export_data
    assert "settings" in export_data
    assert "error_logs" in export_data
    assert "error_patterns" in export_data
    assert "confusion_pairs" in export_data
    assert "personal_dictionary" in export_data
    assert "progress_snapshots" in export_data

    # Verify data is not empty
    assert export_data["user"]["id"] == user.id
    assert len(export_data["error_logs"]) > 0
    assert len(export_data["error_patterns"]) > 0
    assert len(export_data["confusion_pairs"]) > 0
    assert len(export_data["personal_dictionary"]) > 0
    assert len(export_data["progress_snapshots"]) > 0


@pytest.mark.asyncio
async def test_delete_user_cascades(test_user_with_data, db):
    """Deleting user should cascade to all related tables."""
    user = test_user_with_data
    user_id = user.id

    # Verify data exists before deletion
    error_logs_before = await error_log_repo.get_error_logs_by_user(db, user_id)
    patterns_before = await user_error_pattern_repo.get_top_patterns(db, user_id)
    pairs_before = await user_confusion_pair_repo.get_pairs_for_user(db, user_id)
    dict_before = await personal_dictionary_repo.get_dictionary(db, user_id)
    snapshots_before = await progress_snapshot_repo.get_snapshots(db, user_id)

    assert len(error_logs_before) > 0
    assert len(patterns_before) > 0
    assert len(pairs_before) > 0
    assert len(dict_before) > 0
    assert len(snapshots_before) > 0

    # Delete user
    await user_repo.delete_user(db, user)
    await db.commit()

    # Verify cascaded deletion - all related data should be gone
    error_logs_after = await error_log_repo.get_error_logs_by_user(db, user_id)
    patterns_after = await user_error_pattern_repo.get_top_patterns(db, user_id)
    pairs_after = await user_confusion_pair_repo.get_pairs_for_user(db, user_id)
    dict_after = await personal_dictionary_repo.get_dictionary(db, user_id)
    snapshots_after = await progress_snapshot_repo.get_snapshots(db, user_id)

    assert len(error_logs_after) == 0, "Error logs should be cascade deleted"
    assert len(patterns_after) == 0, "Error patterns should be cascade deleted"
    assert len(pairs_after) == 0, "Confusion pairs should be cascade deleted"
    assert len(dict_after) == 0, "Personal dictionary should be cascade deleted"
    assert len(snapshots_after) == 0, "Progress snapshots should be cascade deleted"

    # Verify user no longer exists
    user_after = await user_repo.get_user_by_id(db, user_id)
    assert user_after is None, "User should be deleted"


@pytest.mark.asyncio
async def test_export_data_with_no_activity(db):
    """Export should work even if user has no activity data."""
    # Create user with only default settings
    user = User(
        id=str(uuid.uuid4()),
        email="empty@example.com",
        name="Empty User",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user)
    await settings_repo.create_default_settings(db, user.id)
    await db.commit()

    # Get all data (should be empty except user and settings)
    settings = await settings_repo.get_or_create_settings(db, user.id)
    error_logs = await error_log_repo.get_error_logs_by_user(db, user.id)
    error_patterns = await user_error_pattern_repo.get_top_patterns(db, user.id)

    # Verify structure is valid even with empty data
    assert settings is not None
    assert len(error_logs) == 0
    assert len(error_patterns) == 0


@pytest.mark.asyncio
async def test_settings_cascade_delete(db):
    """User settings should be cascade deleted with user."""
    user = User(
        id=str(uuid.uuid4()),
        email="settings@example.com",
        name="Settings User",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user)
    await settings_repo.create_default_settings(db, user.id)
    await db.commit()

    # Verify settings exist
    settings_before = await settings_repo.get_settings_by_user_id(db, user.id)
    assert settings_before is not None

    # Delete user
    await user_repo.delete_user(db, user)
    await db.commit()

    # Verify settings are cascade deleted
    settings_after = await settings_repo.get_settings_by_user_id(db, user.id)
    assert settings_after is None
