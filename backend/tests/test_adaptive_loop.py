"""Tests for adaptive learning loop functionality."""

import pytest
from datetime import datetime, UTC

from app.core.adaptive_loop import (
    TextSnapshot,
    UserCorrection,
    process_snapshot_pair,
    _tokenize,
    _compute_word_changes,
    _calculate_similarity,
    _levenshtein_distance,
    _classify_error_type,
    _has_letter_reversal,
    _is_phonetically_similar,
    _are_homophones,
    _is_omission_or_addition,
)


class TestTokenize:
    """Tests for text tokenization."""

    def test_basic_tokenization(self):
        assert _tokenize("hello world") == ["hello", "world"]

    def test_multiple_spaces(self):
        assert _tokenize("hello  world   test") == ["hello", "world", "test"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_whitespace_only(self):
        assert _tokenize("   ") == []


class TestComputeWordChanges:
    """Tests for word-level change detection using difflib."""

    def test_no_changes(self):
        old = ["hello", "world"]
        new = ["hello", "world"]
        changes = _compute_word_changes(old, new)
        assert len(changes) == 0

    def test_single_substitution(self):
        old = ["the", "teh", "cat"]
        new = ["the", "the", "cat"]
        changes = _compute_word_changes(old, new)

        assert len(changes) == 1
        assert changes[0]["type"] == "replace"
        assert changes[0]["old_value"] == "teh"
        assert changes[0]["new_value"] == "the"

    def test_insertion(self):
        old = ["the", "cat"]
        new = ["the", "quick", "cat"]
        changes = _compute_word_changes(old, new)

        assert len(changes) == 1
        assert changes[0]["type"] == "add"
        assert changes[0]["new_value"] == "quick"

    def test_deletion(self):
        old = ["the", "quick", "cat"]
        new = ["the", "cat"]
        changes = _compute_word_changes(old, new)

        assert len(changes) == 1
        assert changes[0]["type"] == "remove"
        assert changes[0]["old_value"] == "quick"

    def test_empty_sequences(self):
        assert _compute_word_changes([], []) == []
        changes = _compute_word_changes(["a"], [])
        assert len(changes) == 1
        assert changes[0]["type"] == "remove"
        changes = _compute_word_changes([], ["a"])
        assert len(changes) == 1
        assert changes[0]["type"] == "add"


class TestLevenshteinDistance:
    """Tests for Levenshtein distance calculation."""

    def test_identical_strings(self):
        assert _levenshtein_distance("hello", "hello") == 0

    def test_one_substitution(self):
        assert _levenshtein_distance("hello", "hallo") == 1

    def test_one_insertion(self):
        assert _levenshtein_distance("cat", "cart") == 1

    def test_one_deletion(self):
        assert _levenshtein_distance("cart", "cat") == 1

    def test_multiple_edits(self):
        # "kitten" -> "sitting" requires 3 edits
        assert _levenshtein_distance("kitten", "sitting") == 3

    def test_empty_strings(self):
        assert _levenshtein_distance("", "") == 0
        assert _levenshtein_distance("abc", "") == 3
        assert _levenshtein_distance("", "abc") == 3


class TestCalculateSimilarity:
    """Tests for similarity calculation."""

    def test_identical_words(self):
        assert _calculate_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        similarity = _calculate_similarity("abc", "xyz")
        assert similarity < 0.5

    def test_typo_similarity(self):
        # "teh" vs "the" should be similar
        similarity = _calculate_similarity("teh", "the")
        assert 0.3 < similarity < 0.95

    def test_case_insensitive(self):
        assert _calculate_similarity("Hello", "hello") == 1.0


class TestClassifyErrorType:
    """Tests for error type classification."""

    def test_letter_reversal(self):
        assert _classify_error_type("teh", "the") == "letter_reversal"

    def test_homophone(self):
        assert _classify_error_type("there", "their") == "homophone"
        assert _classify_error_type("your", "you're") == "homophone"

    def test_default_spelling(self):
        # Unrecognized pattern defaults to spelling
        assert _classify_error_type("wrng", "wrong") == "spelling"


class TestHasLetterReversal:
    """Tests for letter reversal detection."""

    def test_simple_reversal(self):
        assert _has_letter_reversal("teh", "the") is True

    def test_no_reversal(self):
        assert _has_letter_reversal("cat", "dog") is False
        assert _has_letter_reversal("hello", "hallo") is False

    def test_different_lengths(self):
        assert _has_letter_reversal("cat", "cart") is False


class TestIsPhoneticallySimilar:
    """Tests for phonetic similarity."""

    def test_similar_consonants(self):
        assert _is_phonetically_similar("phone", "fone") is True

    def test_different_consonants(self):
        assert _is_phonetically_similar("cat", "dog") is False


class TestAreHomophones:
    """Tests for homophone detection."""

    def test_there_their(self):
        assert _are_homophones("there", "their") is True
        assert _are_homophones("their", "there") is True

    def test_to_too_two(self):
        assert _are_homophones("to", "too") is True
        assert _are_homophones("to", "two") is True

    def test_not_homophones(self):
        assert _are_homophones("cat", "dog") is False
        assert _are_homophones("hello", "world") is False


class TestIsOmissionOrAddition:
    """Tests for letter omission/addition detection."""

    def test_one_letter_added(self):
        assert _is_omission_or_addition("cat", "cart") is True

    def test_one_letter_removed(self):
        assert _is_omission_or_addition("cart", "cat") is True

    def test_no_omission(self):
        assert _is_omission_or_addition("cat", "dog") is False

    def test_multiple_differences(self):
        assert _is_omission_or_addition("cat", "carts") is False


@pytest.mark.asyncio
class TestProcessSnapshotPair:
    """Integration tests for snapshot processing."""

    async def test_self_correction_detected(self, db_session):
        """Test that self-corrections are detected from snapshot pairs."""
        before = TextSnapshot(
            text="I saw teh cat yesterday",
            timestamp=datetime.now(UTC),
            word_count=5,
        )
        after = TextSnapshot(
            text="I saw the cat yesterday",
            timestamp=datetime.now(UTC),
            word_count=5,
        )

        corrections = await process_snapshot_pair(
            before, after, user_id="test_user", db=db_session
        )

        # Should detect "teh" -> "the" correction
        assert len(corrections) >= 1
        correction = next((c for c in corrections if c.original == "teh"), None)
        assert correction is not None
        assert correction.corrected == "the"
        assert correction.correction_type == "letter_reversal"
        assert 0.3 < correction.confidence < 0.95

    async def test_no_changes(self, db_session):
        """Test that identical snapshots produce no corrections."""
        text = "The quick brown fox"
        before = TextSnapshot(text=text, timestamp=datetime.now(UTC), word_count=4)
        after = TextSnapshot(text=text, timestamp=datetime.now(UTC), word_count=4)

        corrections = await process_snapshot_pair(
            before, after, user_id="test_user", db=db_session
        )

        assert len(corrections) == 0

    async def test_multiple_corrections(self, db_session):
        """Test detection of multiple corrections in one snapshot."""
        before = TextSnapshot(
            text="I saw teh cat becuase it was there",
            timestamp=datetime.now(UTC),
            word_count=8,
        )
        after = TextSnapshot(
            text="I saw the cat because it was there",
            timestamp=datetime.now(UTC),
            word_count=8,
        )

        corrections = await process_snapshot_pair(
            before, after, user_id="test_user", db=db_session
        )

        # Should detect both "teh" -> "the" and "becuase" -> "because"
        assert len(corrections) >= 2

        originals = {c.original for c in corrections}
        assert "teh" in originals
        assert "becuase" in originals

    async def test_large_rewrite_ignored(self, db_session):
        """Test that large rewrites are not flagged as self-corrections."""
        before = TextSnapshot(
            text="The cat sat on the mat",
            timestamp=datetime.now(UTC),
            word_count=6,
        )
        after = TextSnapshot(
            text="A dog stood near the door",
            timestamp=datetime.now(UTC),
            word_count=6,
        )

        corrections = await process_snapshot_pair(
            before, after, user_id="test_user", db=db_session
        )

        # Large rewrites should not produce corrections
        # (similarity too low for "cat"/"dog", "sat"/"stood", etc.)
        assert len(corrections) == 0
