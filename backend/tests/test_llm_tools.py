"""Tests for LLM tool definitions and executor."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm_tools import (
    check_confusion_pair,
    execute_tool,
    lookup_word,
)


# ---------------------------------------------------------------------------
# TestLookupWord
# ---------------------------------------------------------------------------


class TestLookupWord:
    """Tests for the lookup_word tool."""

    @patch("app.core.llm_tools._frequency_dict", {"the", "hello", "world", "because"})
    def test_valid_word(self):
        result = lookup_word("hello")
        assert result["is_valid"] is True
        assert result["word"] == "hello"

    @patch("app.core.llm_tools._frequency_dict", {"the", "hello", "world"})
    def test_invalid_word(self):
        result = lookup_word("xyznotaword")
        assert result["is_valid"] is False

    @patch("app.core.llm_tools._frequency_dict", {"because"})
    def test_case_insensitive(self):
        result = lookup_word("BECAUSE")
        assert result["is_valid"] is True

    @patch("app.core.llm_tools._frequency_dict", {"hello"})
    def test_strips_whitespace(self):
        result = lookup_word("  hello  ")
        assert result["is_valid"] is True


# ---------------------------------------------------------------------------
# TestCheckConfusionPair
# ---------------------------------------------------------------------------


class TestCheckConfusionPair:
    """Tests for the check_confusion_pair tool."""

    @patch(
        "app.core.llm_tools._confusion_pairs",
        [{"words": ["their", "there", "they're"], "category": "homophone", "frequency": "very_high"}],
    )
    def test_known_pair(self):
        result = check_confusion_pair("their", "there")
        assert result["is_confusion_pair"] is True
        assert result["category"] == "homophone"

    @patch(
        "app.core.llm_tools._confusion_pairs",
        [{"words": ["their", "there", "they're"], "category": "homophone", "frequency": "very_high"}],
    )
    def test_unknown_pair(self):
        result = check_confusion_pair("cat", "dog")
        assert result["is_confusion_pair"] is False

    @patch(
        "app.core.llm_tools._confusion_pairs",
        [{"words": ["affect", "effect"], "category": "homophone", "frequency": "high"}],
    )
    def test_case_insensitive(self):
        result = check_confusion_pair("AFFECT", "Effect")
        assert result["is_confusion_pair"] is True


# ---------------------------------------------------------------------------
# TestExecuteTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExecuteTool:
    """Tests for the execute_tool dispatcher."""

    @patch("app.core.llm_tools._frequency_dict", {"hello"})
    async def test_dispatches_lookup_word(self):
        result = json.loads(await execute_tool("lookup_word", {"word": "hello"}))
        assert result["is_valid"] is True

    @patch(
        "app.core.llm_tools._confusion_pairs",
        [{"words": ["their", "there"], "category": "homophone", "frequency": "high"}],
    )
    async def test_dispatches_check_confusion_pair(self):
        result = json.loads(
            await execute_tool("check_confusion_pair", {"word_a": "their", "word_b": "there"})
        )
        assert result["is_confusion_pair"] is True

    async def test_unknown_tool_returns_error(self):
        result = json.loads(await execute_tool("nonexistent_tool", {}))
        assert "error" in result
        assert "Unknown tool" in result["error"]

    async def test_get_user_error_history_needs_db(self):
        result = json.loads(
            await execute_tool("get_user_error_history", {"misspelling": "teh"})
        )
        assert "error" in result

    async def test_check_personal_dictionary_needs_db(self):
        result = json.loads(
            await execute_tool("check_personal_dictionary", {"word": "pokemon"})
        )
        assert "error" in result
