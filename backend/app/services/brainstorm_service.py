"""
Service for AI brainstorm conversation turns via LLM.

Sends proper multi-turn messages to the 30B Nemotron model for
conversation memory and question-answering support.
Sub-idea extraction is deferred to the final extraction pass.
"""

import logging
import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.brainstorm import BrainstormTurnResponse
from app.core.brainstorm_prompts import (
    BRAINSTORM_SYSTEM_PROMPT,
    build_brainstorm_context,
)
from app.services.tts_service import text_to_speech

logger = logging.getLogger(__name__)

_ROLE_MAP = {"user": "user", "ai": "assistant"}


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=2, max=15),
    retry=retry_if_exception_type((httpx.ConnectError,)),
)
async def _call_brainstorm_llm(
    messages: list[dict],
    model: str,
    max_tokens: int,
) -> dict:
    """Call NIM chat/completions with retry on connection errors."""
    url = f"{settings.nvidia_nim_llm_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=10.0)
    ) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


class BrainstormService:
    """Handles brainstorm conversation turns via NVIDIA NIM."""

    async def process_turn(
        self,
        user_utterance: str,
        conversation_history: list[dict],
        existing_cards: list[dict],
        transcript_so_far: str,
    ) -> BrainstormTurnResponse:
        """
        Process a single brainstorm conversation turn.

        Builds a proper multi-turn messages array so the LLM sees real
        conversation history instead of a flattened text blob.
        """
        if not settings.nvidia_nim_api_key:
            logger.warning("NVIDIA_NIM_API_KEY not set — brainstorm will fail")
            return BrainstormTurnResponse(
                reply="I'd love to brainstorm, but the AI service isn't configured yet.",
            )

        # --- Build system message with context ---
        system_content = BRAINSTORM_SYSTEM_PROMPT
        context = build_brainstorm_context(existing_cards, transcript_so_far)
        if context:
            system_content += context

        messages: list[dict] = [{"role": "system", "content": system_content}]

        # --- Append conversation history as proper multi-turn messages ---
        max_turns = settings.brainstorm_max_history_turns
        recent = conversation_history[-max_turns:]
        for turn in recent:
            role = _ROLE_MAP.get(turn.get("role", ""), "user")
            content = turn.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

        # --- Append the current user utterance ---
        messages.append({"role": "user", "content": user_utterance})

        model = settings.brainstorm_llm_model
        max_tokens = settings.brainstorm_max_tokens

        logger.debug(
            "Brainstorm LLM request: model=%s, turns=%d, utterance=%d chars",
            model, len(messages) - 1, len(user_utterance),
        )

        start_time = time.monotonic()

        try:
            result = await _call_brainstorm_llm(messages, model, max_tokens)
            elapsed = time.monotonic() - start_time
            logger.info("Brainstorm LLM response: elapsed=%.1fs", elapsed)

            message = result["choices"][0]["message"]
            content = (message.get("content") or "").strip()

            logger.debug(
                "Brainstorm LLM message fields: content=%d chars, "
                "has_reasoning_content=%s, has_reasoning=%s",
                len(content),
                "reasoning_content" in message,
                "reasoning" in message,
            )

            # Nemotron reasoning model: if content is empty, the actual
            # reply may be in the reasoning field
            if not content:
                reasoning = (
                    message.get("reasoning_content")
                    or message.get("reasoning")
                    or ""
                )
                if reasoning:
                    logger.info(
                        "Content empty — extracting reply from reasoning "
                        "(%d chars)", len(reasoning),
                    )
                    content = self._extract_reply_from_reasoning(reasoning)
                else:
                    logger.warning(
                        "Content empty and no reasoning field found. "
                        "Message keys: %s", list(message.keys()),
                    )

            if not content:
                logger.warning("No usable content from LLM — using fallback reply")
                content = "That's interesting — tell me more about that?"

            logger.info("Brainstorm reply (%d chars): %s", len(content), content[:200])

            # Generate TTS audio for the reply via MagpieTTS
            audio_url = ""
            try:
                audio_url = await text_to_speech(content)
                if audio_url:
                    logger.info("Brainstorm TTS audio: %s", audio_url)
                else:
                    logger.warning("Brainstorm TTS returned empty URL")
            except Exception as tts_err:
                logger.warning("Brainstorm TTS failed: %s", tts_err)

            return BrainstormTurnResponse(reply=content, audio_url=audio_url)

        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "Brainstorm LLM timeout after %.1fs: %s: %s",
                elapsed, type(e).__name__, e,
            )
            return BrainstormTurnResponse(
                reply="I lost my train of thought — could you say that again?",
            )
        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "Brainstorm LLM HTTP error after %.1fs: status=%d, body=%s",
                elapsed, e.response.status_code,
                e.response.text[:500] if e.response.text else "(empty)",
            )
            return BrainstormTurnResponse(
                reply="I lost my train of thought — could you say that again?",
            )
        except httpx.HTTPError as e:
            elapsed = time.monotonic() - start_time
            logger.error(
                "Brainstorm LLM network error after %.1fs: %s: %s",
                elapsed, type(e).__name__, e,
            )
            return BrainstormTurnResponse(
                reply="I lost my train of thought — could you say that again?",
            )
        except (KeyError, IndexError) as e:
            logger.error(
                "Failed to parse brainstorm LLM response: %s: %s",
                type(e).__name__, e, exc_info=True,
            )
            return BrainstormTurnResponse(
                reply="I lost my train of thought — could you say that again?",
            )

    @staticmethod
    def _extract_reply_from_reasoning(reasoning: str) -> str:
        """Try to extract a conversational reply from the model's reasoning text.

        When the model runs out of content tokens, the actual reply is
        sometimes embedded in the reasoning. Look for quoted replies or
        the last few sentences.
        """
        import re

        # Look for a quoted reply in the reasoning
        quoted = re.findall(r'"([^"]{10,200})"', reasoning)
        if quoted:
            # Return the last substantial quoted string
            for q in reversed(quoted):
                if "?" in q or len(q) > 20:
                    return q

        # Fall back to the last 1-2 sentences of reasoning
        sentences = [s.strip() for s in reasoning.split(".") if s.strip()]
        if sentences:
            last = sentences[-1]
            if len(last) > 10:
                return last + ("" if last.endswith("?") else "?")

        return ""


# Singleton instance
brainstorm_service = BrainstormService()
