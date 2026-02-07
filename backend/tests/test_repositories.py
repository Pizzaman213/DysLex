"""Unit tests for the 4 new repository modules."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import (
    error_log_repo,
    personal_dictionary_repo,
    user_confusion_pair_repo,
    user_error_pattern_repo,
)


# ---------------------------------------------------------------------------
# user_error_pattern_repo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_pattern_creates(db: AsyncSession, test_user: User):
    """First upsert should create a new pattern with frequency 1."""
    pattern = await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "teh", "the", "reversal"
    )
    assert pattern.frequency == 1
    assert pattern.misspelling == "teh"
    assert pattern.correction == "the"


@pytest.mark.asyncio
async def test_upsert_pattern_increments(db: AsyncSession, test_user: User):
    """Repeated upserts should increment frequency."""
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "teh", "the", "reversal"
    )
    pattern = await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "teh", "the", "reversal"
    )
    assert pattern.frequency == 2


@pytest.mark.asyncio
async def test_get_top_patterns_order(db: AsyncSession, test_user: User):
    """Top patterns should be ordered by frequency descending."""
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "becuase", "because", "phonetic"
    )
    for _ in range(3):
        await user_error_pattern_repo.upsert_pattern(
            db, test_user.id, "teh", "the", "reversal"
        )

    top = await user_error_pattern_repo.get_top_patterns(db, test_user.id)
    assert len(top) == 2
    assert top[0].misspelling == "teh"
    assert top[0].frequency == 3


@pytest.mark.asyncio
async def test_get_error_type_counts(db: AsyncSession, test_user: User):
    """Error type counts should aggregate correctly."""
    for _ in range(2):
        await user_error_pattern_repo.upsert_pattern(
            db, test_user.id, "teh", "the", "reversal"
        )
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "becuase", "because", "phonetic"
    )

    counts = await user_error_pattern_repo.get_error_type_counts(db, test_user.id)
    counts_dict = {etype: total for etype, total in counts}
    assert counts_dict["reversal"] == 2
    assert counts_dict["phonetic"] == 1


@pytest.mark.asyncio
async def test_get_pattern_count(db: AsyncSession, test_user: User):
    """Pattern count should reflect distinct patterns."""
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "teh", "the", "reversal"
    )
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "teh", "the", "reversal"
    )
    await user_error_pattern_repo.upsert_pattern(
        db, test_user.id, "becuase", "because", "phonetic"
    )

    count = await user_error_pattern_repo.get_pattern_count(db, test_user.id)
    assert count == 2


# ---------------------------------------------------------------------------
# user_confusion_pair_repo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_confusion_pair_normalizes(db: AsyncSession, test_user: User):
    """Confusion pairs should be alphabetically normalized."""
    pair = await user_confusion_pair_repo.upsert_confusion_pair(
        db, test_user.id, "there", "their"
    )
    assert pair.word_a == "their"
    assert pair.word_b == "there"
    assert pair.confusion_count == 1


@pytest.mark.asyncio
async def test_upsert_confusion_pair_increments(db: AsyncSession, test_user: User):
    """Repeated upserts should increment the count."""
    await user_confusion_pair_repo.upsert_confusion_pair(
        db, test_user.id, "there", "their"
    )
    pair = await user_confusion_pair_repo.upsert_confusion_pair(
        db, test_user.id, "their", "there"  # reversed order
    )
    assert pair.confusion_count == 2


@pytest.mark.asyncio
async def test_get_pairs_for_user(db: AsyncSession, test_user: User):
    """Should return all pairs ordered by count."""
    await user_confusion_pair_repo.upsert_confusion_pair(
        db, test_user.id, "there", "their"
    )
    for _ in range(3):
        await user_confusion_pair_repo.upsert_confusion_pair(
            db, test_user.id, "your", "you're"
        )

    pairs = await user_confusion_pair_repo.get_pairs_for_user(db, test_user.id)
    assert len(pairs) == 2
    # "your/you're" should be first (count=3)
    assert pairs[0].confusion_count == 3


# ---------------------------------------------------------------------------
# personal_dictionary_repo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_and_check_word(db: AsyncSession, test_user: User):
    """Adding a word should make check_word return True."""
    assert not await personal_dictionary_repo.check_word(db, test_user.id, "pytest")
    await personal_dictionary_repo.add_word(db, test_user.id, "PyTest")
    assert await personal_dictionary_repo.check_word(db, test_user.id, "pytest")


@pytest.mark.asyncio
async def test_add_word_idempotent(db: AsyncSession, test_user: User):
    """Adding the same word twice should not create duplicates."""
    await personal_dictionary_repo.add_word(db, test_user.id, "hello")
    await personal_dictionary_repo.add_word(db, test_user.id, "hello")
    entries = await personal_dictionary_repo.get_dictionary(db, test_user.id)
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_remove_word(db: AsyncSession, test_user: User):
    """Removing a word should make check_word return False."""
    await personal_dictionary_repo.add_word(db, test_user.id, "test")
    removed = await personal_dictionary_repo.remove_word(db, test_user.id, "test")
    assert removed
    assert not await personal_dictionary_repo.check_word(db, test_user.id, "test")


@pytest.mark.asyncio
async def test_remove_nonexistent_word(db: AsyncSession, test_user: User):
    """Removing a word that doesn't exist should return False."""
    removed = await personal_dictionary_repo.remove_word(
        db, test_user.id, "nonexistent"
    )
    assert not removed


# ---------------------------------------------------------------------------
# error_log_repo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_error_log(db: AsyncSession, test_user: User):
    """Should create and return an error log entry."""
    log = await error_log_repo.create_error_log(
        db=db,
        user_id=test_user.id,
        original_text="teh",
        corrected_text="the",
        error_type="reversal",
        source="self_corrected",
    )
    assert log.original_text == "teh"
    assert log.source == "self_corrected"


@pytest.mark.asyncio
async def test_get_error_logs_by_user(db: AsyncSession, test_user: User):
    """Should return logs for the user."""
    await error_log_repo.create_error_log(
        db=db,
        user_id=test_user.id,
        original_text="teh",
        corrected_text="the",
        error_type="reversal",
    )
    logs = await error_log_repo.get_error_logs_by_user(db, test_user.id)
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_get_error_count_by_period(db: AsyncSession, test_user: User):
    """Should count recent errors."""
    for _ in range(3):
        await error_log_repo.create_error_log(
            db=db,
            user_id=test_user.id,
            original_text="teh",
            corrected_text="the",
            error_type="reversal",
        )
    count = await error_log_repo.get_error_count_by_period(db, test_user.id, days=14)
    assert count == 3
