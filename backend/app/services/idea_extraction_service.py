"""
Service for extracting idea cards from transcripts via LLM.
"""

import logging
from typing import List
import httpx

from app.config import settings
from app.models.capture import ThoughtCard, SubIdea
from app.core.capture_prompts import EXTRACT_IDEAS_SYSTEM_PROMPT, build_extract_ideas_prompt
from app.utils.json_parser import parse_json_from_llm_response

logger = logging.getLogger(__name__)


def _validate_and_fix_cards(cards: List[ThoughtCard]) -> List[ThoughtCard]:
    """Validate and fix parsed cards to ensure consistent structure."""
    fixed = []
    for i, card in enumerate(cards):
        # Ensure IDs are present
        if not card.id:
            card.id = f"topic-{i + 1}"

        # Ensure sub_ideas have IDs
        valid_subs = []
        for j, sub in enumerate(card.sub_ideas):
            if not sub.id:
                sub.id = f"{card.id}-sub-{j + 1}"
            if sub.title.strip():
                valid_subs.append(sub)
        card.sub_ideas = valid_subs

        if card.title.strip():
            fixed.append(card)

    return fixed


class IdeaExtractionService:
    """Extracts thought cards from transcripts using Nemotron via NIM."""

    async def extract_ideas(self, transcript: str) -> List[ThoughtCard]:
        """
        Extract thought cards with sub-ideas from a transcript.

        Args:
            transcript: The transcript text to analyze

        Returns:
            List of ThoughtCard objects with nested sub_ideas

        Raises:
            httpx.HTTPError: If the API request fails
        """
        if not settings.nvidia_nim_api_key:
            logger.warning("NVIDIA_NIM_API_KEY not set — idea extraction will fail")
            return []

        url = f"{settings.nvidia_nim_llm_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.nvidia_nim_llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": EXTRACT_IDEAS_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": build_extract_ideas_prompt(transcript)
                }
            ],
            "temperature": 0.4,
            "max_tokens": 2048
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                logger.debug(f"LLM raw response: {content[:500]}")

                cards = parse_json_from_llm_response(
                    content=content,
                    model_class=ThoughtCard,
                    is_array=True
                )

                cards = _validate_and_fix_cards(cards)

                logger.info(
                    f"Extracted {len(cards)} topics with "
                    f"{sum(len(c.sub_ideas) for c in cards)} total sub-ideas"
                )

                return cards

        except httpx.HTTPError as e:
            logger.error(f"Idea extraction failed: {e}")
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []


# Singleton instance
idea_extraction_service = IdeaExtractionService()
