"""
Service for extracting idea cards from transcripts via LLM.
"""

import json
import logging
from typing import List, Tuple
import httpx

from app.config import settings
from app.models.capture import ThoughtCard, SubIdea
from app.core.capture_prompts import EXTRACT_IDEAS_SYSTEM_PROMPT, build_extract_ideas_prompt
from app.utils.json_parser import parse_json_from_llm_response

logger = logging.getLogger(__name__)


def _validate_and_fix_cards(cards: List[ThoughtCard], original_text: str = "") -> List[ThoughtCard]:
    """Validate and fix parsed cards to ensure consistent structure."""
    fixed = []
    seen_titles: set[str] = set()
    original_lower = original_text.strip().lower()

    for i, card in enumerate(cards):
        if not card.title.strip():
            continue

        # Deduplicate by title
        title_key = card.title.strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # Ensure IDs are present
        if not card.id:
            card.id = f"topic-{i + 1}"

        # Fix body: if the LLM dumped the entire input text verbatim, use just the title
        body_lower = card.body.strip().lower()
        if original_lower and body_lower == original_lower:
            card.body = card.title
            logger.warning(f"Card '{card.title}' had full input as body — replaced with title")

        # Ensure sub_ideas have IDs and filter duplicates
        valid_subs = []
        seen_sub_titles: set[str] = set()
        for j, sub in enumerate(card.sub_ideas):
            if not sub.id:
                sub.id = f"{card.id}-sub-{j + 1}"
            sub_title_key = sub.title.strip().lower()
            if sub.title.strip() and sub_title_key not in seen_sub_titles:
                # Skip sub-ideas that just repeat the topic body
                sub_body_lower = sub.body.strip().lower()
                if sub_body_lower != body_lower:
                    seen_sub_titles.add(sub_title_key)
                    valid_subs.append(sub)
        card.sub_ideas = valid_subs

        fixed.append(card)

    return fixed


def _fix_raw_card(card_dict: dict) -> dict:
    """Fill in missing required fields on raw card dicts before Pydantic validation."""
    for sub in card_dict.get("sub_ideas", []):
        if isinstance(sub, dict) and not sub.get("title"):
            # Derive title from body (first ~8 words) or fall back to id
            body = sub.get("body", "")
            if body:
                words = body.split()
                sub["title"] = " ".join(words[:8]) + ("..." if len(words) > 8 else "")
            else:
                sub["title"] = sub.get("id", "Untitled")
    return card_dict


class IdeaExtractionService:
    """Extracts thought cards from transcripts using Nemotron via NIM."""

    async def extract_ideas(
        self,
        transcript: str,
        existing_titles: list[str] | None = None,
    ) -> Tuple[List[ThoughtCard], str]:
        """
        Extract thought cards with sub-ideas from a transcript.

        Args:
            transcript: The transcript text to analyze
            existing_titles: Titles already extracted (for incremental dedup)

        Returns:
            Tuple of (list of ThoughtCard objects, central topic string)

        Raises:
            httpx.HTTPError: If the API request fails
        """
        if not settings.nvidia_nim_api_key:
            logger.warning("NVIDIA_NIM_API_KEY not set — idea extraction will fail")
            return [], ""

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
                    "content": build_extract_ideas_prompt(transcript, existing_titles)
                }
            ],
            "temperature": 0.4,
            "max_tokens": settings.llm_max_tokens
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

                logger.info(f"LLM raw response: {content[:500]}")

                # Try parsing as {topic, cards} object first
                topic = ""
                cards: List[ThoughtCard] = []

                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        topic = parsed.get("topic", "")
                        raw_cards = parsed.get("cards", [])
                        cards = [ThoughtCard(**_fix_raw_card(c)) if isinstance(c, dict) else c for c in raw_cards]
                    elif isinstance(parsed, list):
                        # Backward compat: LLM returned a plain array
                        cards = [ThoughtCard(**_fix_raw_card(c)) if isinstance(c, dict) else c for c in parsed]
                except (json.JSONDecodeError, TypeError):
                    # Fall back to the existing parser
                    cards = parse_json_from_llm_response(
                        content=content,
                        model_class=ThoughtCard,
                        is_array=True
                    )

                cards = _validate_and_fix_cards(cards, original_text=transcript)

                logger.info(
                    f"Extracted {len(cards)} topics with "
                    f"{sum(len(c.sub_ideas) for c in cards)} total sub-ideas"
                    f" (topic: '{topic}')"
                )

                return cards, topic

        except httpx.HTTPError as e:
            logger.error(f"Idea extraction API error: {e}")
            return [], ""
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return [], ""


# Singleton instance
idea_extraction_service = IdeaExtractionService()
