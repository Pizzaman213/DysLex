"""Tests for Nemotron deep analysis client (Tier 2)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.correction import Correction, Position
from app.services.nemotron_client import (
    DeepAnalysisError,
    _compute_positions,
    _split_into_chunks,
    _split_long_paragraph,
    parse_nemotron_response,
)


# ---------------------------------------------------------------------------
# Pure unit tests — chunking
# ---------------------------------------------------------------------------


class TestSplitIntoChunks:
    """Tests for _split_into_chunks."""

    def test_short_text_single_chunk(self):
        text = "Hello world."
        chunks = _split_into_chunks(text, 100)
        assert chunks == [text]

    def test_splits_on_paragraph_boundary(self):
        para1 = "First paragraph."
        para2 = "Second paragraph."
        text = f"{para1}\n\n{para2}"
        chunks = _split_into_chunks(text, len(para1) + 5)
        assert len(chunks) == 2
        assert chunks[0] == para1
        assert chunks[1] == para2

    def test_keeps_small_paragraphs_together(self):
        text = "A.\n\nB.\n\nC."
        chunks = _split_into_chunks(text, 100)
        assert chunks == [text]

    def test_long_single_paragraph_splits_on_sentences(self):
        sentences = [f"Sentence {i}." for i in range(20)]
        text = " ".join(sentences)
        chunks = _split_into_chunks(text, 60)
        assert len(chunks) > 1
        # All text preserved
        reconstructed = " ".join(chunks)
        for s in sentences:
            assert s in reconstructed

    def test_empty_text(self):
        assert _split_into_chunks("", 100) == [""]

    def test_exact_max_chars(self):
        text = "A" * 100
        chunks = _split_into_chunks(text, 100)
        assert chunks == [text]


class TestSplitLongParagraph:
    """Tests for _split_long_paragraph."""

    def test_splits_on_sentence_boundaries(self):
        para = "First sentence. Second sentence. Third sentence."
        chunks = _split_long_paragraph(para, 35)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 35 or "." in chunk

    def test_single_sentence(self):
        para = "A single very long sentence without periods that goes on and on"
        chunks = _split_long_paragraph(para, 20)
        # Without sentence boundaries, each "sentence" (the whole thing) becomes a chunk
        assert len(chunks) >= 1

    def test_empty_paragraph(self):
        # Empty string splits into no sentences, so returns empty list
        assert _split_long_paragraph("", 100) == []


# ---------------------------------------------------------------------------
# Pure unit tests — position computation
# ---------------------------------------------------------------------------


class TestComputePositions:
    """Tests for _compute_positions."""

    def test_finds_correction_positions(self):
        text = "I saw teh cat"
        corrections = [Correction(original="teh", correction="the")]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 6
        assert corrections[0].position.end == 9

    def test_skips_already_positioned(self):
        text = "I saw teh cat"
        pos = Position(start=99, end=102)
        corrections = [Correction(original="teh", correction="the", position=pos)]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 99  # unchanged

    def test_handles_missing_original(self):
        text = "some text"
        corrections = [Correction(original="", correction="fix")]
        _compute_positions(text, corrections)
        assert corrections[0].position is None

    def test_handles_not_found(self):
        text = "hello world"
        corrections = [Correction(original="xyz", correction="abc")]
        _compute_positions(text, corrections)
        assert corrections[0].position is None

    def test_multiple_occurrences_get_distinct_positions(self):
        text = "the cat and the dog"
        corrections = [
            Correction(original="the", correction="a"),
            Correction(original="the", correction="a"),
        ]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 0
        assert corrections[1].position is not None
        assert corrections[1].position.start == 12

    def test_out_of_order_retry(self):
        text = "cat dog cat"
        corrections = [
            Correction(original="dog", correction="pup"),
            Correction(original="cat", correction="kitten"),
        ]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 4
        # Second "cat" search starts after "dog", so finds the second one at index 8
        assert corrections[1].position is not None
        assert corrections[1].position.start == 8

    def test_case_insensitive_fallback(self):
        """LLM returns different casing — should still find the word."""
        text = "I saw The cat"
        corrections = [Correction(original="the", correction="a")]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 6
        assert corrections[0].position.end == 9

    def test_case_insensitive_fallback_uppercase_original(self):
        """LLM returns uppercase original for a lowercase word in text."""
        text = "she went becuase of rain"
        corrections = [Correction(original="Becuase", correction="because")]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 9
        assert corrections[0].position.end == 16

    def test_stripped_fallback(self):
        """LLM wraps original with punctuation — stripped search should match."""
        text = "I like teh cat"
        corrections = [Correction(original='"teh"', correction="the")]
        _compute_positions(text, corrections)
        assert corrections[0].position is not None
        assert corrections[0].position.start == 7
        assert corrections[0].position.end == 10

    def test_unfindable_correction_gets_no_position(self):
        """Correction that genuinely doesn't exist in text stays positionless."""
        text = "hello world"
        corrections = [Correction(original="xyzzy", correction="magic")]
        _compute_positions(text, corrections)
        assert corrections[0].position is None


# ---------------------------------------------------------------------------
# Pure unit tests — response parsing
# ---------------------------------------------------------------------------


class TestParseNemotronResponse:
    """Tests for parse_nemotron_response."""

    def test_valid_response(self):
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            {"original": "teh", "suggested": "the", "type": "spelling"}
                        ])
                    }
                }
            ]
        }
        result = parse_nemotron_response(response)
        assert len(result) == 1
        assert result[0].original == "teh"
        assert result[0].correction == "the"

    def test_empty_corrections_array(self):
        response = {
            "choices": [{"message": {"content": "[]"}}]
        }
        result = parse_nemotron_response(response)
        assert result == []

    def test_malformed_response_missing_choices(self):
        result = parse_nemotron_response({})
        assert result == []

    def test_malformed_response_missing_message(self):
        result = parse_nemotron_response({"choices": [{}]})
        assert result == []

    def test_response_with_markdown_fences(self):
        content = '```json\n[{"original": "becuase", "suggested": "because", "type": "spelling"}]\n```'
        response = {"choices": [{"message": {"content": content}}]}
        result = parse_nemotron_response(response)
        assert len(result) == 1
        assert result[0].original == "becuase"


# ---------------------------------------------------------------------------
# Mock-based async tests — deep_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeepAnalysis:
    """Tests for the deep_analysis function."""

    @patch("app.services.nemotron_client.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.services.nemotron_client.get_system_default_config")
    async def test_no_api_key_returns_empty(self, mock_config, mock_cache):
        from app.services.llm_client import LLMProvider, LLMProviderConfig
        from app.services.nemotron_client import deep_analysis

        mock_config.return_value = LLMProviderConfig(
            provider=LLMProvider.nvidia_nim,
            base_url="https://test.api",
            model="test-model",
            api_key="",
        )
        result = await deep_analysis("text", "user-1")
        assert result == []

    @patch("app.services.nemotron_client.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.services.nemotron_client.get_system_default_config")
    async def test_no_api_key_raises_when_requested(self, mock_config, mock_cache):
        from app.services.llm_client import LLMProvider, LLMProviderConfig
        from app.services.nemotron_client import deep_analysis

        mock_config.return_value = LLMProviderConfig(
            provider=LLMProvider.nvidia_nim,
            base_url="https://test.api",
            model="test-model",
            api_key="",
        )
        with pytest.raises(DeepAnalysisError, match="not configured"):
            await deep_analysis("text", "user-1", raise_on_error=True)

    @patch("app.services.nemotron_client._call_nim_api", new_callable=AsyncMock)
    @patch("app.services.nemotron_client.settings")
    async def test_single_chunk_analysis(self, mock_settings, mock_api):
        from app.services.nemotron_client import deep_analysis

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_api.return_value = [
            Correction(original="teh", correction="the", position=Position(start=6, end=9)),
        ]

        result = await deep_analysis("I saw teh cat", "user-1")
        assert len(result) == 1
        assert result[0].original == "teh"
        mock_api.assert_awaited_once()

    @patch("app.services.nemotron_client._call_nim_api", new_callable=AsyncMock)
    @patch("app.services.nemotron_client.settings")
    async def test_chunk_failure_returns_empty_by_default(self, mock_settings, mock_api):
        from app.services.nemotron_client import deep_analysis

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_api.side_effect = httpx.TimeoutException("timeout")

        result = await deep_analysis("short text", "user-1")
        assert result == []


@pytest.mark.asyncio
class TestCallNimApi:
    """Tests for _call_nim_api with mocked httpx."""

    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_successful_call(self, mock_settings, mock_client_cls):
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": '[{"original": "teh", "suggested": "the", "type": "spelling"}]'}}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        messages = [{"role": "user", "content": "test prompt"}]
        result = await _call_nim_api(messages)
        assert len(result) == 1
        assert result[0].original == "teh"

    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_http_error_raises(self, mock_settings, mock_client_cls):
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        messages = [{"role": "user", "content": "test prompt"}]
        with pytest.raises(httpx.HTTPStatusError):
            await _call_nim_api(messages)


# ---------------------------------------------------------------------------
# Tool calling tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestToolCalling:
    """Tests for tool calling loop in _call_nim_api."""

    def _make_mock_response(self, data, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = data
        mock_response.text = json.dumps(data)
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def _make_mock_client(self, responses):
        """Create mock client that returns different responses on successive calls."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=responses)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_no_tool_calls_returns_normally(self, mock_settings, mock_client_cls):
        """Model responds with content and no tool_calls — works as before."""
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.llm_max_tokens = 1024
        mock_settings.llm_tool_calling_max_rounds = 3

        response_data = {
            "choices": [{"message": {"content": '[{"original": "teh", "suggested": "the", "type": "spelling"}]'}}]
        }
        mock_response = self._make_mock_response(response_data)
        mock_client = self._make_mock_client([mock_response])
        mock_client_cls.return_value = mock_client

        tools = [{"type": "function", "function": {"name": "lookup_word", "parameters": {}}}]
        result = await _call_nim_api(
            [{"role": "user", "content": "test"}],
            tools=tools,
        )
        assert len(result) == 1
        assert result[0].original == "teh"

    @patch("app.core.llm_tools.execute_tool", new_callable=AsyncMock)
    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_single_tool_call_round(self, mock_settings, mock_client_cls, mock_execute):
        """Model calls a tool in round 1, then returns content in round 2."""
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.llm_max_tokens = 1024
        mock_settings.llm_tool_calling_max_rounds = 3

        # Round 1: model requests a tool call
        tool_call_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "lookup_word",
                            "arguments": '{"word": "becuase"}',
                        },
                    }],
                },
            }],
        }
        # Round 2: model returns corrections
        content_response = {
            "choices": [{
                "message": {
                    "content": '[{"original": "becuase", "suggested": "because", "type": "spelling"}]',
                },
            }],
        }

        mock_execute.return_value = '{"word": "becuase", "is_valid": false}'

        responses = [
            self._make_mock_response(tool_call_response),
            self._make_mock_response(content_response),
        ]
        mock_client = self._make_mock_client(responses)
        mock_client_cls.return_value = mock_client

        tools = [{"type": "function", "function": {"name": "lookup_word", "parameters": {}}}]
        result = await _call_nim_api(
            [{"role": "user", "content": "I went becuase"}],
            tools=tools,
        )

        assert len(result) == 1
        assert result[0].original == "becuase"
        mock_execute.assert_awaited_once()

    @patch("app.core.llm_tools.execute_tool", new_callable=AsyncMock)
    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_max_rounds_prevents_infinite_loop(self, mock_settings, mock_client_cls, mock_execute):
        """Model always returns tool_calls — stops at max_rounds."""
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.llm_max_tokens = 1024
        mock_settings.llm_tool_calling_max_rounds = 2

        tool_call_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "lookup_word", "arguments": '{"word": "test"}'},
                    }],
                },
            }],
        }
        # Final round: tools omitted, model forced to respond with content
        final_response = {
            "choices": [{"message": {"content": "[]"}}]
        }

        mock_execute.return_value = '{"word": "test", "is_valid": true}'

        # Round 1 returns tool calls, Round 2 (final, no tools) returns content
        responses = [
            self._make_mock_response(tool_call_response),
            self._make_mock_response(final_response),
        ]
        mock_client = self._make_mock_client(responses)
        mock_client_cls.return_value = mock_client

        tools = [{"type": "function", "function": {"name": "lookup_word", "parameters": {}}}]
        result = await _call_nim_api(
            [{"role": "user", "content": "test"}],
            tools=tools,
        )

        # Should return empty corrections from the "[]" response
        assert result == []
        # Only 1 tool execution (round 1 had tools, round 2 did not)
        assert mock_execute.await_count == 1

    @patch("app.services.nemotron_client.httpx.AsyncClient")
    @patch("app.services.nemotron_client.settings")
    async def test_tools_not_included_when_disabled(self, mock_settings, mock_client_cls):
        """When tools=None, payload should not contain 'tools' key."""
        from app.services.nemotron_client import _call_nim_api

        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.llm_max_tokens = 1024
        mock_settings.llm_tool_calling_max_rounds = 3

        response_data = {
            "choices": [{"message": {"content": "[]"}}]
        }
        mock_response = self._make_mock_response(response_data)
        mock_client = self._make_mock_client([mock_response])
        mock_client_cls.return_value = mock_client

        await _call_nim_api([{"role": "user", "content": "test"}])

        # Check the payload sent to the API
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "tools" not in payload
        assert "tool_choice" not in payload
