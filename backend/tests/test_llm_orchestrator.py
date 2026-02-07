"""Tests for two-tier LLM processing orchestrator."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm_orchestrator import (
    _merge_corrections,
    _needs_deep_analysis,
    auto_route,
    deep_only,
    document_review,
    quick_only,
)
from app.models.correction import Correction, Position


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


class TestNeedsDeepAnalysis:
    """Tests for the _needs_deep_analysis heuristic."""

    def test_short_text_with_results_no_deep(self):
        corrections = [Correction(original="teh", correction="the")]
        assert _needs_deep_analysis("short text", corrections) is False

    def test_long_text_triggers_deep(self):
        long_text = " ".join(["word"] * 25)
        assert _needs_deep_analysis(long_text, []) is True

    def test_empty_corrections_triggers_deep(self):
        assert _needs_deep_analysis("some text here", []) is True

    def test_exactly_20_words_no_deep(self):
        text = " ".join(["word"] * 20)
        corrections = [Correction(original="a", correction="b")]
        assert _needs_deep_analysis(text, corrections) is False

    def test_21_words_triggers_deep(self):
        text = " ".join(["word"] * 21)
        corrections = [Correction(original="a", correction="b")]
        assert _needs_deep_analysis(text, corrections) is True


class TestMergeCorrections:
    """Tests for _merge_corrections."""

    def test_no_overlap(self):
        confident = [
            Correction(original="teh", correction="the", position=Position(start=0, end=3)),
        ]
        deep = [
            Correction(original="becuase", correction="because", position=Position(start=10, end=17)),
        ]
        merged = _merge_corrections(confident, deep)
        assert len(merged) == 2

    def test_deep_overrides_on_overlap(self):
        confident = [
            Correction(original="teh", correction="the", position=Position(start=0, end=3), tier="quick"),
        ]
        deep = [
            Correction(original="teh", correction="the", position=Position(start=0, end=3), tier="deep"),
        ]
        merged = _merge_corrections(confident, deep)
        assert len(merged) == 1
        assert merged[0].tier == "deep"

    def test_no_position_corrections_kept(self):
        confident = [Correction(original="a", correction="b", position=None)]
        deep = [Correction(original="c", correction="d", position=None)]
        merged = _merge_corrections(confident, deep)
        assert len(merged) == 2

    def test_empty_inputs(self):
        assert _merge_corrections([], []) == []

    def test_mixed_positioned_and_unpositioned(self):
        confident = [
            Correction(original="a", correction="b", position=Position(start=0, end=1)),
            Correction(original="c", correction="d", position=None),
        ]
        deep = [
            Correction(original="e", correction="f", position=None),
        ]
        merged = _merge_corrections(confident, deep)
        assert len(merged) == 3


# ---------------------------------------------------------------------------
# Mock-based async tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestQuickOnly:
    """Tests for quick_only endpoint."""

    @patch("app.core.llm_orchestrator.quick_correction", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_returns_quick_corrections(self, mock_profile, mock_quick, db):
        mock_profile.return_value = None
        expected = [Correction(original="teh", correction="the")]
        mock_quick.return_value = expected

        result = await quick_only("I saw teh cat", "user-1", db)
        assert result == expected
        mock_quick.assert_awaited_once()

    @patch("app.core.llm_orchestrator.quick_correction", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_returns_empty_when_no_errors(self, mock_profile, mock_quick, db):
        mock_profile.return_value = None
        mock_quick.return_value = []

        result = await quick_only("Perfect text", "user-1", db)
        assert result == []


@pytest.mark.asyncio
class TestDeepOnly:
    """Tests for deep_only endpoint."""

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_returns_deep_corrections(self, mock_profile, mock_deep, db):
        mock_profile.return_value = None
        mock_deep.return_value = [
            Correction(original="there", correction="their", error_type="homophone"),
        ]

        result = await deep_only("I went to there house", "user-1", db=db)
        assert len(result) == 1
        assert result[0].tier == "deep"

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_sets_tier_to_deep(self, mock_profile, mock_deep, db):
        mock_profile.return_value = None
        mock_deep.return_value = [
            Correction(original="a", correction="b", tier="quick"),
        ]

        result = await deep_only("text", "user-1", db=db)
        assert all(c.tier == "deep" for c in result)


@pytest.mark.asyncio
class TestAutoRoute:
    """Tests for confidence-based auto_route."""

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.quick_correction", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_confident_corrections_skip_deep(self, mock_profile, mock_quick, mock_deep, db):
        mock_profile.return_value = None
        mock_quick.return_value = [
            Correction(original="teh", correction="the", confidence=0.95),
        ]

        result = await auto_route("teh cat", "user-1", db=db)
        # Short text (2 words) + confident corrections -> no deep call
        # But _needs_deep_analysis checks word count > 20, so 2 words won't trigger
        # However, len(quick_results) > 0, so no deep from empty results
        # Still, word_count=2 <= 20 and len(quick_results)=1 > 0, so no deep
        mock_deep.assert_not_awaited()
        assert len(result) == 1

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.quick_correction", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_low_confidence_triggers_deep(self, mock_profile, mock_quick, mock_deep, db):
        mock_profile.return_value = None
        mock_quick.return_value = [
            Correction(original="there", correction="their", confidence=0.5),
        ]
        mock_deep.return_value = [
            Correction(original="there", correction="their", confidence=0.95,
                        position=Position(start=0, end=5)),
        ]

        result = await auto_route("there house is big", "user-1", db=db)
        mock_deep.assert_awaited_once()
        assert len(result) >= 1

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.quick_correction", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_long_text_always_triggers_deep(self, mock_profile, mock_quick, mock_deep, db):
        mock_profile.return_value = None
        long_text = " ".join(["word"] * 25)
        mock_quick.return_value = [
            Correction(original="word", correction="word", confidence=0.99),
        ]
        mock_deep.return_value = []

        await auto_route(long_text, "user-1", db=db)
        mock_deep.assert_awaited_once()


@pytest.mark.asyncio
class TestDocumentReview:
    """Tests for document_review."""

    @patch("app.core.llm_orchestrator.deep_analysis", new_callable=AsyncMock)
    @patch("app.core.llm_orchestrator.get_user_profile", new_callable=AsyncMock)
    async def test_delegates_to_deep_only(self, mock_profile, mock_deep, db):
        mock_profile.return_value = None
        mock_deep.return_value = [
            Correction(original="teh", correction="the"),
        ]

        result = await document_review("teh cat", "user-1", db=db)
        mock_deep.assert_awaited_once()
        assert len(result) == 1
        # raise_on_error should be True
        call_kwargs = mock_deep.call_args
        assert call_kwargs.kwargs.get("raise_on_error") is True
