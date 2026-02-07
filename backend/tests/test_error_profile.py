"""Tests for the ErrorProfileService."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_profile import error_profile_service
from app.db.models import User
from app.models.error_log import ErrorTypeBreakdown, FullErrorProfile, LLMContext


# ---------------------------------------------------------------------------
# Full profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_full_profile_empty(db: AsyncSession, test_user: User):
    """New user should have an empty profile with default score."""
    profile = await error_profile_service.get_full_profile(test_user.id, db)
    assert isinstance(profile, FullErrorProfile)
    assert profile.user_id == test_user.id
    assert profile.top_errors == []
    assert profile.confusion_pairs == []
    assert profile.personal_dictionary == []
    assert profile.patterns_mastered == 0
    assert profile.total_patterns == 0
    assert profile.overall_score == 50  # default


@pytest.mark.asyncio
async def test_get_full_profile_with_data(db: AsyncSession, test_user: User):
    """Profile should reflect logged errors."""
    await error_profile_service.log_error(
        test_user.id, db, "teh", "the", "reversal"
    )
    await error_profile_service.log_error(
        test_user.id, db, "teh", "the", "reversal"
    )
    await error_profile_service.log_error(
        test_user.id, db, "becuase", "because", "phonetic"
    )

    profile = await error_profile_service.get_full_profile(test_user.id, db)
    assert profile.total_patterns == 2
    assert len(profile.top_errors) == 2
    # "teh" should be first (frequency=2)
    assert profile.top_errors[0].misspelling == "teh"
    assert profile.top_errors[0].frequency == 2


# ---------------------------------------------------------------------------
# log_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_error_creates_pattern(db: AsyncSession, test_user: User):
    """log_error should create a pattern entry."""
    await error_profile_service.log_error(
        test_user.id, db, "recieve", "receive", "phonetic"
    )
    top = await error_profile_service.get_top_errors(test_user.id, db)
    assert len(top) == 1
    assert top[0].misspelling == "recieve"
    assert top[0].frequency == 1


@pytest.mark.asyncio
async def test_log_error_increments_frequency(db: AsyncSession, test_user: User):
    """Repeated log_error for the same misspelling should increment frequency."""
    for _ in range(5):
        await error_profile_service.log_error(
            test_user.id, db, "teh", "the", "reversal"
        )
    top = await error_profile_service.get_top_errors(test_user.id, db)
    assert len(top) == 1
    assert top[0].frequency == 5


@pytest.mark.asyncio
async def test_log_error_homophone_creates_confusion_pair(
    db: AsyncSession, test_user: User
):
    """Logging a homophone error should auto-create a confusion pair."""
    await error_profile_service.log_error(
        test_user.id, db, "there", "their", "homophone"
    )
    pairs = await error_profile_service.get_confusion_pairs(test_user.id, db)
    assert len(pairs) == 1
    # Alphabetically normalized
    assert pairs[0].word_a == "their"
    assert pairs[0].word_b == "there"


# ---------------------------------------------------------------------------
# build_llm_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_llm_context_empty(db: AsyncSession, test_user: User):
    """LLM context for a new user should have sensible defaults."""
    ctx = await error_profile_service.build_llm_context(test_user.id, db)
    assert isinstance(ctx, LLMContext)
    assert ctx.writing_level == "new_user"
    assert ctx.top_errors == []
    assert ctx.confusion_pairs == []
    assert ctx.personal_dictionary == []


@pytest.mark.asyncio
async def test_build_llm_context_populated(db: AsyncSession, test_user: User):
    """LLM context should include logged errors."""
    await error_profile_service.log_error(
        test_user.id, db, "teh", "the", "reversal"
    )
    await error_profile_service.add_to_dictionary(test_user.id, db, "DysLex")

    ctx = await error_profile_service.build_llm_context(test_user.id, db)
    assert len(ctx.top_errors) == 1
    assert ctx.top_errors[0]["misspelling"] == "teh"
    assert "dyslex" in ctx.personal_dictionary


# ---------------------------------------------------------------------------
# Personal dictionary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dictionary_add_check_remove(db: AsyncSession, test_user: User):
    """Add, check, and remove a word from the personal dictionary."""
    assert not await error_profile_service.check_personal_dictionary(
        test_user.id, db, "pytest"
    )

    await error_profile_service.add_to_dictionary(test_user.id, db, "PyTest")
    assert await error_profile_service.check_personal_dictionary(
        test_user.id, db, "pytest"
    )

    removed = await error_profile_service.remove_from_dictionary(
        test_user.id, db, "pytest"
    )
    assert removed
    assert not await error_profile_service.check_personal_dictionary(
        test_user.id, db, "pytest"
    )


# ---------------------------------------------------------------------------
# Error type breakdown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_type_breakdown(db: AsyncSession, test_user: User):
    """Breakdown should compute correct percentages."""
    for _ in range(3):
        await error_profile_service.log_error(
            test_user.id, db, "teh", "the", "reversal"
        )
    await error_profile_service.log_error(
        test_user.id, db, "becuase", "because", "phonetic"
    )

    breakdown = await error_profile_service.get_error_type_breakdown(
        test_user.id, db
    )
    assert isinstance(breakdown, ErrorTypeBreakdown)
    assert breakdown.reversal == 75.0
    assert breakdown.phonetic == 25.0


# ---------------------------------------------------------------------------
# detect_improvement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_improvement_new_user(db: AsyncSession, test_user: User):
    """New user with no errors should report 'new_user' trend."""
    result = await error_profile_service.detect_improvement(test_user.id, db)
    assert result["trend"] == "new_user"
