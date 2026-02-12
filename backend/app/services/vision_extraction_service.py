"""
Service for extracting idea cards from images via NVIDIA NIM vision model.
"""

import json
import logging
import re
from typing import List, Tuple

import httpx

from app.config import settings
from app.core.vision_prompts import VISION_EXTRACT_SYSTEM_PROMPT, build_vision_extract_prompt
from app.models.capture import ThoughtCard
from app.services.idea_extraction_service import _validate_and_fix_cards
from app.utils.json_parser import parse_json_from_llm_response

logger = logging.getLogger(__name__)


def _parse_cosmos_response(content: str) -> dict:
    """Parse Cosmos Reason2 response, handling <think>/<answer> tags."""
    # Cosmos may wrap output in <think>...</think><answer>...</answer> tags
    answer_match = re.search(r"<answer>(.*?)</answer>", content, re.DOTALL)
    if answer_match:
        content = answer_match.group(1).strip()

    # Try direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding a JSON object anywhere in the text
    obj_match = re.search(r"\{.*\"cards\"\s*:\s*\[.*\].*\}", content, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


class VisionExtractionService:
    """Extracts thought cards from images using NVIDIA NIM vision model."""

    async def extract_ideas_from_image(
        self,
        image_base64: str,
        mime_type: str = "image/jpeg",
        user_hint: str | None = None,
    ) -> Tuple[List[ThoughtCard], str]:
        """
        Extract thought cards from an image.

        Args:
            image_base64: Base64-encoded image data
            mime_type: MIME type of the image (e.g. "image/jpeg", "image/png")
            user_hint: Optional hint about what the image contains

        Returns:
            Tuple of (list of ThoughtCard objects, central topic string)
        """
        if not settings.nvidia_nim_api_key:
            logger.warning("NVIDIA_NIM_API_KEY not set — vision extraction will fail")
            return [], ""

        url = f"{settings.nvidia_nim_llm_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
            "Content-Type": "application/json",
        }

        data_uri = f"data:{mime_type};base64,{image_base64}"

        payload = {
            "model": settings.nvidia_nim_vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": VISION_EXTRACT_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                        {
                            "type": "text",
                            "text": build_vision_extract_prompt(user_hint),
                        },
                    ],
                },
            ],
            "temperature": 0.4,
            "max_tokens": 2048,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                logger.info(f"Vision LLM raw response ({len(content)} chars): {content[:1000]}")

                parsed = _parse_cosmos_response(content)
                if not parsed or (isinstance(parsed, dict) and not parsed.get("cards")):
                    logger.warning(f"Vision parse produced no cards. Full content: {content[:2000]}")

                topic = parsed.get("topic", "") if isinstance(parsed, dict) else ""
                raw_cards = parsed.get("cards", []) if isinstance(parsed, dict) else []

                cards: List[ThoughtCard] = []
                if raw_cards:
                    cards = [
                        ThoughtCard(**c) if isinstance(c, dict) else c
                        for c in raw_cards
                    ]
                else:
                    # Fallback: try parsing as array
                    cards = parse_json_from_llm_response(
                        content=content,
                        model_class=ThoughtCard,
                        is_array=True,
                    )

                cards = _validate_and_fix_cards(cards)

                logger.info(
                    f"Vision extracted {len(cards)} topics with "
                    f"{sum(len(c.sub_ideas) for c in cards)} total sub-ideas"
                    f" (topic: '{topic}')"
                )

                return cards, topic

        except httpx.HTTPError as e:
            logger.error(f"Vision extraction failed: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse vision LLM response: {e}")
            return [], ""


# Singleton instance
vision_extraction_service = VisionExtractionService()
