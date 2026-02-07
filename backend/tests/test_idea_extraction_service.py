"""Tests for idea extraction service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.capture import SubIdea, ThoughtCard
from app.services.idea_extraction_service import (
    IdeaExtractionService,
    _validate_and_fix_cards,
)


# ---------------------------------------------------------------------------
# Pure unit tests — _validate_and_fix_cards
# ---------------------------------------------------------------------------


class TestValidateAndFixCards:
    """Tests for _validate_and_fix_cards."""

    def test_valid_cards_pass_through(self):
        cards = [
            ThoughtCard(id="topic-1", title="Dogs are great", body="Dogs are loyal."),
            ThoughtCard(id="topic-2", title="Cats are cool", body="Cats are independent."),
        ]
        result = _validate_and_fix_cards(cards)
        assert len(result) == 2

    def test_empty_title_filtered(self):
        cards = [
            ThoughtCard(id="topic-1", title="", body="Some body"),
            ThoughtCard(id="topic-2", title="Valid title", body="Valid body"),
        ]
        result = _validate_and_fix_cards(cards)
        assert len(result) == 1
        assert result[0].title == "Valid title"

    def test_duplicate_titles_deduplicated(self):
        cards = [
            ThoughtCard(id="topic-1", title="Same Title", body="Body 1"),
            ThoughtCard(id="topic-2", title="Same Title", body="Body 2"),
        ]
        result = _validate_and_fix_cards(cards)
        assert len(result) == 1

    def test_missing_id_gets_assigned(self):
        cards = [ThoughtCard(id="", title="No ID", body="Body")]
        result = _validate_and_fix_cards(cards)
        assert result[0].id == "topic-1"

    def test_body_matching_full_input_replaced(self):
        original = "Dogs are great and cats are cool"
        cards = [
            ThoughtCard(id="topic-1", title="Animals", body="Dogs are great and cats are cool"),
        ]
        result = _validate_and_fix_cards(cards, original_text=original)
        assert result[0].body == "Animals"

    def test_sub_ideas_validated(self):
        cards = [
            ThoughtCard(
                id="topic-1",
                title="Main",
                body="Main body",
                sub_ideas=[
                    SubIdea(id="", title="Sub 1", body="Sub body 1"),
                    SubIdea(id="s2", title="", body="Empty title"),
                    SubIdea(id="s3", title="Sub 3", body="Sub body 3"),
                ],
            ),
        ]
        result = _validate_and_fix_cards(cards)
        assert len(result[0].sub_ideas) == 2  # empty title filtered
        assert result[0].sub_ideas[0].id == "topic-1-sub-1"  # ID assigned

    def test_sub_ideas_duplicating_body_filtered(self):
        cards = [
            ThoughtCard(
                id="topic-1",
                title="Main",
                body="Exact same body",
                sub_ideas=[
                    SubIdea(id="s1", title="Sub", body="Exact same body"),
                ],
            ),
        ]
        result = _validate_and_fix_cards(cards)
        assert len(result[0].sub_ideas) == 0

    def test_empty_list(self):
        assert _validate_and_fix_cards([]) == []


# ---------------------------------------------------------------------------
# Mock-based async tests — IdeaExtractionService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestIdeaExtractionService:
    """Tests for IdeaExtractionService.extract_ideas."""

    @patch("app.services.idea_extraction_service.settings")
    async def test_no_api_key_returns_empty(self, mock_settings):
        mock_settings.nvidia_nim_api_key = ""
        service = IdeaExtractionService()
        cards, topic = await service.extract_ideas("some transcript")
        assert cards == []
        assert topic == ""

    @patch("app.services.idea_extraction_service.httpx.AsyncClient")
    @patch("app.services.idea_extraction_service.settings")
    async def test_successful_extraction(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        response_data = {
            "topic": "Technology",
            "cards": [
                {"id": "topic-1", "title": "AI is powerful", "body": "AI transforms industries.", "sub_ideas": []},
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(response_data)}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = IdeaExtractionService()
        cards, topic = await service.extract_ideas("AI is changing the world")

        assert topic == "Technology"
        assert len(cards) == 1
        assert cards[0].title == "AI is powerful"

    @patch("app.services.idea_extraction_service.httpx.AsyncClient")
    @patch("app.services.idea_extraction_service.settings")
    async def test_http_error_raises(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = IdeaExtractionService()
        with pytest.raises(httpx.HTTPError):
            await service.extract_ideas("some transcript")

    @patch("app.services.idea_extraction_service.httpx.AsyncClient")
    @patch("app.services.idea_extraction_service.settings")
    async def test_malformed_json_returns_empty(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "not valid json at all"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = IdeaExtractionService()
        cards, topic = await service.extract_ideas("some transcript")
        assert cards == []

    @patch("app.services.idea_extraction_service.httpx.AsyncClient")
    @patch("app.services.idea_extraction_service.settings")
    async def test_backward_compat_plain_array(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_model = "test-model"
        mock_settings.nvidia_nim_llm_url = "https://test.api"

        array_data = [
            {"id": "topic-1", "title": "Idea One", "body": "Body one.", "sub_ideas": []},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(array_data)}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = IdeaExtractionService()
        cards, topic = await service.extract_ideas("some text")
        assert len(cards) == 1
        assert topic == ""
