"""Tests for progress repository."""

import uuid

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ErrorLog, User
from app.db.repositories import progress_repo


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        password_hash="hashed",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def sample_error_logs(db: AsyncSession, test_user):
    """Create sample error logs for testing."""
    now = datetime.utcnow()
    logs = []

    # Create errors over 12 weeks
    for week in range(12):
        week_date = now - timedelta(weeks=week)
        for _ in range(5):  # 5 errors per week
            log = ErrorLog(
                id=f"log-{week}-{_}",
                user_id=test_user.id,
                original_text="teh",
                corrected_text="the",
                error_type="spelling",
                created_at=week_date,
            )
            logs.append(log)
            db.add(log)

    # Add self-corrections for mastered words
    for i in range(5):
        log = ErrorLog(
            id=f"self-{i}",
            user_id=test_user.id,
            original_text="becuase",
            corrected_text="because",
            error_type="self-correction",
            created_at=now - timedelta(days=i),
        )
        logs.append(log)
        db.add(log)

    await db.commit()
    return logs


@pytest.mark.asyncio
async def test_get_error_frequency_by_week(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching error frequency by week."""
    result = await progress_repo.get_error_frequency_by_week(db, test_user.id, weeks=12)

    assert len(result) > 0
    assert all("week_start" in item for item in result)
    assert all("total_errors" in item for item in result)
    assert all(isinstance(item["total_errors"], int) for item in result)


@pytest.mark.asyncio
async def test_get_error_breakdown_by_type(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching error breakdown by type."""
    result = await progress_repo.get_error_breakdown_by_type(db, test_user.id, weeks=12)

    assert len(result) > 0
    assert all("week_start" in item for item in result)
    assert all("spelling" in item for item in result)
    assert all("grammar" in item for item in result)


@pytest.mark.asyncio
async def test_get_top_errors(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching top errors."""
    result = await progress_repo.get_top_errors(db, test_user.id, limit=10, weeks=12)

    assert len(result) > 0
    assert all("original" in item for item in result)
    assert all("corrected" in item for item in result)
    assert all("frequency" in item for item in result)


@pytest.mark.asyncio
async def test_get_mastered_words(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching mastered words."""
    result = await progress_repo.get_mastered_words(db, test_user.id, weeks=4)

    assert len(result) > 0
    assert all("word" in item for item in result)
    assert all("times_corrected" in item for item in result)
    assert all(item["times_corrected"] >= 3 for item in result)


@pytest.mark.asyncio
async def test_get_writing_streak(db: AsyncSession, test_user, sample_error_logs):
    """Test calculating writing streak."""
    result = await progress_repo.get_writing_streak(db, test_user.id)

    assert "current_streak" in result
    assert "longest_streak" in result
    assert "last_activity" in result
    assert isinstance(result["current_streak"], int)
    assert isinstance(result["longest_streak"], int)


@pytest.mark.asyncio
async def test_get_total_stats(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching total stats."""
    result = await progress_repo.get_total_stats(db, test_user.id)

    assert "total_words" in result
    assert "total_corrections" in result
    assert "total_sessions" in result
    assert result["total_corrections"] > 0


@pytest.mark.asyncio
async def test_get_improvement_by_error_type(db: AsyncSession, test_user, sample_error_logs):
    """Test fetching improvement by error type."""
    result = await progress_repo.get_improvement_by_error_type(db, test_user.id, weeks=12)

    assert len(result) > 0
    assert all("error_type" in item for item in result)
    assert all("change_percent" in item for item in result)
    assert all("trend" in item for item in result)
    assert all("sparkline_data" in item for item in result)
    assert all(item["trend"] in ["improving", "stable", "needs_attention"] for item in result)


@pytest.mark.asyncio
async def test_empty_user_data(db: AsyncSession):
    """Test with user that has no error logs."""
    empty_user = User(
        id=str(uuid.uuid4()),
        email="empty@example.com",
        name="Empty User",
        password_hash="hashed",
    )
    db.add(empty_user)
    await db.commit()

    # All functions should return empty arrays/zero values without errors
    freq = await progress_repo.get_error_frequency_by_week(db, empty_user.id)
    assert freq == []

    breakdown = await progress_repo.get_error_breakdown_by_type(db, empty_user.id)
    assert breakdown == []

    top = await progress_repo.get_top_errors(db, empty_user.id)
    assert top == []

    mastered = await progress_repo.get_mastered_words(db, empty_user.id)
    assert mastered == []

    streak = await progress_repo.get_writing_streak(db, empty_user.id)
    assert streak["current_streak"] == 0
    assert streak["longest_streak"] == 0

    stats = await progress_repo.get_total_stats(db, empty_user.id)
    assert stats["total_corrections"] == 0
