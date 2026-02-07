"""Tests for vision extraction service (Cosmos Reason2 8B)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.capture import ThoughtCard
from app.services.vision_extraction_service import (
    VisionExtractionService,
    _parse_cosmos_response,
)


# ---------------------------------------------------------------------------
# Pure unit tests — _parse_cosmos_response
# ---------------------------------------------------------------------------


class TestParseCosmosResponse:
    """Tests for _parse_cosmos_response."""

    def test_direct_json(self):
        content = json.dumps({"topic": "Tech", "cards": [{"id": "1", "title": "A"}]})
        result = _parse_cosmos_response(content)
        assert result["topic"] == "Tech"
        assert len(result["cards"]) == 1

    def test_answer_tags(self):
        content = '<think>reasoning here</think><answer>{"topic": "Math", "cards": []}</answer>'
        result = _parse_cosmos_response(content)
        assert result["topic"] == "Math"
        assert result["cards"] == []

    def test_markdown_code_fence(self):
        content = 'Here is the result:\n```json\n{"topic": "Science", "cards": []}\n```'
        result = _parse_cosmos_response(content)
        assert result["topic"] == "Science"

    def test_embedded_json_object(self):
        content = 'Some text {"topic": "Art", "cards": [{"id": "1", "title": "Painting"}]} more text'
        result = _parse_cosmos_response(content)
        assert result["topic"] == "Art"

    def test_completely_invalid_returns_empty(self):
        result = _parse_cosmos_response("no json here at all")
        assert result == {}

    def test_empty_string(self):
        result = _parse_cosmos_response("")
        assert result == {}

    def test_nested_answer_content(self):
        inner = json.dumps({"topic": "History", "cards": [{"id": "t1", "title": "WW2", "body": "desc", "sub_ideas": []}]})
        content = f"<think>let me think</think><answer>{inner}</answer>"
        result = _parse_cosmos_response(content)
        assert result["topic"] == "History"
        assert len(result["cards"]) == 1


# ---------------------------------------------------------------------------
# Mock-based async tests — VisionExtractionService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestVisionExtractionService:
    """Tests for VisionExtractionService.extract_ideas_from_image."""

    @patch("app.services.vision_extraction_service.settings")
    async def test_no_api_key_returns_empty(self, mock_settings):
        mock_settings.nvidia_nim_api_key = ""
        service = VisionExtractionService()
        cards, topic = await service.extract_ideas_from_image("base64data", "image/jpeg")
        assert cards == []
        assert topic == ""

    @patch("app.services.vision_extraction_service.httpx.AsyncClient")
    @patch("app.services.vision_extraction_service.settings")
    async def test_successful_extraction(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.nvidia_nim_vision_model = "test-vision-model"

        response_data = {
            "topic": "Class Notes",
            "cards": [
                {"id": "topic-1", "title": "Key concept", "body": "Important idea.", "sub_ideas": []},
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

        service = VisionExtractionService()
        cards, topic = await service.extract_ideas_from_image("base64data", "image/jpeg")

        assert topic == "Class Notes"
        assert len(cards) == 1
        assert cards[0].title == "Key concept"

    @patch("app.services.vision_extraction_service.httpx.AsyncClient")
    @patch("app.services.vision_extraction_service.settings")
    async def test_passes_user_hint(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.nvidia_nim_vision_model = "test-vision-model"

        response_data = {
            "topic": "Notes",
            "cards": [
                {"id": "topic-1", "title": "Idea", "body": "Details.", "sub_ideas": []},
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

        service = VisionExtractionService()
        await service.extract_ideas_from_image("base64data", "image/png", user_hint="whiteboard photo")
        # Verify the hint made it into the request payload
        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        user_content = payload["messages"][1]["content"]
        text_parts = [p["text"] for p in user_content if p.get("type") == "text"]
        assert any("whiteboard photo" in t for t in text_parts)

    @patch("app.services.vision_extraction_service.httpx.AsyncClient")
    @patch("app.services.vision_extraction_service.settings")
    async def test_http_error_raises(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.nvidia_nim_vision_model = "test-vision-model"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = VisionExtractionService()
        with pytest.raises(httpx.HTTPError):
            await service.extract_ideas_from_image("base64data", "image/jpeg")

    @patch("app.services.vision_extraction_service.httpx.AsyncClient")
    @patch("app.services.vision_extraction_service.settings")
    async def test_malformed_response_returns_empty(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.nvidia_nim_vision_model = "test-vision-model"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "totally not json"}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = VisionExtractionService()
        cards, topic = await service.extract_ideas_from_image("base64data", "image/jpeg")
        assert cards == []

    @patch("app.services.vision_extraction_service.httpx.AsyncClient")
    @patch("app.services.vision_extraction_service.settings")
    async def test_cosmos_think_answer_tags(self, mock_settings, mock_client_cls):
        mock_settings.nvidia_nim_api_key = "test-key"
        mock_settings.nvidia_nim_llm_url = "https://test.api"
        mock_settings.nvidia_nim_vision_model = "test-vision-model"

        inner = json.dumps({
            "topic": "Biology",
            "cards": [
                {"id": "topic-1", "title": "Cells", "body": "Building blocks of life.", "sub_ideas": []},
            ],
        })
        content = f"<think>analyzing image</think><answer>{inner}</answer>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        service = VisionExtractionService()
        cards, topic = await service.extract_ideas_from_image("base64data", "image/jpeg")

        assert topic == "Biology"
        assert len(cards) == 1
        assert cards[0].title == "Cells"
