"""Nemotron client for deep text analysis (Tier 2)."""

import asyncio
import json
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.core.prompt_builder import build_correction_prompt, build_correction_prompt_v2
from app.models.correction import Correction, Position
from app.models.error_log import LLMContext
from app.utils.json_parser import parse_json_from_llm_response

logger = logging.getLogger(__name__)

# Maximum characters per chunk sent to the LLM.
# ~3 000 chars ≈ 750 tokens — well within the model's context window
# once the system prompt / profile is added.
_MAX_CHUNK_CHARS = 3000

# Module-level circuit breaker — shared across all deep_analysis calls
_nim_circuit_breaker = CircuitBreaker(
    "nvidia_nim",
    failure_threshold=settings.circuit_breaker_failure_threshold,
    cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
)


def get_circuit_breaker() -> CircuitBreaker:
    """Return the NIM circuit breaker (used by health endpoint)."""
    return _nim_circuit_breaker


class DeepAnalysisError(Exception):
    """Raised when deep analysis cannot be performed."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def deep_analysis(
    text: str,
    user_id: str,
    context: str | None = None,
    profile: object | None = None,
    db: AsyncSession | None = None,
    *,
    raise_on_error: bool = False,
) -> list[Correction]:
    """Perform deep text analysis using Nemotron via NIM API (Tier 2).

    Large documents are automatically split into chunks, analyzed in
    parallel, and the results merged with correct character offsets.

    When *raise_on_error* is True (used by explicit deep/document endpoints),
    failures are raised instead of silently returning an empty list.
    """
    logger.info("=== DEEP ANALYSIS START ===")
    logger.info("Model: %s", settings.nvidia_nim_llm_model)
    logger.info("API URL: %s", settings.nvidia_nim_llm_url)
    logger.info("API key configured: %s", bool(settings.nvidia_nim_api_key))
    logger.info("User: %s | Text length: %d chars", user_id, len(text))

    if not settings.nvidia_nim_api_key:
        logger.error("No API key — aborting deep analysis")
        if raise_on_error:
            raise DeepAnalysisError(
                "NVIDIA_NIM_API_KEY is not configured. "
                "Set it in your .env file or environment variables to enable deep analysis."
            )
        return []

    # Build personalised prompt pieces from the error profile
    llm_context: LLMContext | None = None
    if db is not None:
        from app.core.error_profile import error_profile_service

        try:
            llm_context = await error_profile_service.build_llm_context(user_id, db)
        except Exception:
            logger.warning("Failed to load LLM context for user %s", user_id, exc_info=True)

    # --- chunk the text ------------------------------------------------
    chunks = _split_into_chunks(text, _MAX_CHUNK_CHARS)
    logger.info("Split text into %d chunk(s)", len(chunks))

    # Build one set of messages per chunk
    # Each entry is (messages_list, chunk_offset)
    chunk_messages: list[tuple[list[dict], int]] = []
    offset = 0
    for chunk in chunks:
        if llm_context is not None:
            system_msg, user_msg = build_correction_prompt_v2(chunk, llm_context, context)
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
        else:
            user_patterns: list[dict] = []
            confusion_pairs: list[dict] = []
            if profile is not None:
                user_patterns = getattr(profile, "top_patterns", [])
                confusion_pairs = getattr(profile, "confusion_pairs", [])
            prompt = build_correction_prompt(chunk, user_patterns, confusion_pairs, context)
            messages = [{"role": "user", "content": prompt}]
        total_len = sum(len(m["content"]) for m in messages)
        chunk_messages.append((messages, offset))
        logger.info("  Chunk offset=%d  len=%d  prompt_len=%d", offset, len(chunk), total_len)
        offset += len(chunk)

    # --- Prepare tool definitions if enabled ---
    tools: list[dict] | None = None
    if settings.llm_tool_calling_enabled:
        from app.core.llm_tools import TOOL_DEFINITIONS
        tools = TOOL_DEFINITIONS

    # --- call the LLM for each chunk (parallel, max 3 at a time) ------
    all_corrections: list[Correction] = []

    sem = asyncio.Semaphore(3)

    async def _analyze_chunk(messages: list[dict], chunk_text: str, chunk_offset: int) -> list[Correction]:
        async with sem:
            try:
                corrections = await _nim_circuit_breaker.call(
                    _call_nim_api(messages, tools=tools, user_id=user_id, db=db)
                )
                # Compute positions relative to the chunk text
                _compute_positions(chunk_text, corrections)
                # Shift positions so they're relative to the full document
                for c in corrections:
                    if c.position is not None:
                        c.position = Position(
                            start=c.position.start + chunk_offset,
                            end=c.position.end + chunk_offset,
                        )
                return corrections
            except CircuitBreakerOpen:
                logger.warning("Circuit breaker OPEN — skipping chunk at offset %d", chunk_offset)
                if raise_on_error:
                    raise
                return []
            except Exception as exc:
                logger.warning("Chunk at offset %d failed: %s", chunk_offset, exc)
                if raise_on_error:
                    raise
                return []

    tasks = []
    for i, (messages, chunk_offset) in enumerate(chunk_messages):
        chunk_text = chunks[i]
        tasks.append(_analyze_chunk(messages, chunk_text, chunk_offset))

    results = await asyncio.gather(*tasks, return_exceptions=raise_on_error)

    for result in results:
        if isinstance(result, BaseException):
            raise DeepAnalysisError(f"LLM analysis failed: {result}") from result
        all_corrections.extend(result)

    logger.info("Total corrections across all chunks: %d", len(all_corrections))
    for c in all_corrections:
        logger.info("  Correction: '%s' -> '%s' [%s] pos=%s",
                    c.original, c.correction, c.error_type,
                    f"{c.position.start}-{c.position.end}" if c.position else "none")
    logger.info("=== DEEP ANALYSIS DONE ===")
    return all_corrections


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split *text* into chunks of roughly *max_chars*, breaking on paragraph
    boundaries (double-newline) so we never cut a sentence in half."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        # If a single paragraph is larger than max_chars, split on sentences
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for sentence_chunk in _split_long_paragraph(para, max_chars):
                chunks.append(sentence_chunk)
            continue

        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return chunks


def _split_long_paragraph(para: str, max_chars: int) -> list[str]:
    """Split a single very long paragraph on sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', para)
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        candidate = (current + " " + sent) if current else sent
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Position computation
# ---------------------------------------------------------------------------


def _compute_positions(text: str, corrections: list[Correction]) -> None:
    """Fill in start/end positions for corrections missing them.

    Searches for each correction's ``original`` text in the source and assigns
    the character offsets.  Uses a ``search_from`` cursor so that duplicate
    words get distinct positions.
    """
    search_from = 0
    for c in corrections:
        if c.position is not None:
            continue
        if not c.original:
            continue
        idx = text.find(c.original, search_from)
        if idx == -1:
            # Retry from the beginning (the LLM may have returned them out of order)
            idx = text.find(c.original)
        if idx != -1:
            c.position = Position(start=idx, end=idx + len(c.original))
            search_from = idx + len(c.original)


# ---------------------------------------------------------------------------
# NIM API call
# ---------------------------------------------------------------------------


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=2, max=15),
    retry=retry_if_exception_type((httpx.ConnectError,)),
)
async def _call_nim_api(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    user_id: str | None = None,
    db: AsyncSession | None = None,
) -> list[Correction]:
    """Call NIM API with retry on connection errors only.

    When *tools* is provided and tool calling is enabled, runs a
    conversation loop: if the model returns tool_calls instead of content,
    execute them and feed results back, up to ``llm_tool_calling_max_rounds``.
    """
    url = f"{settings.nvidia_nim_llm_url}/chat/completions"

    # Work on a mutable copy of the conversation
    conversation = list(messages)
    max_rounds = settings.llm_tool_calling_max_rounds if tools else 1

    response_data: dict = {}
    for round_idx in range(max_rounds):
        total_len = sum(len(m.get("content", "") or "") for m in conversation)
        payload: dict = {
            "model": settings.nvidia_nim_llm_model,
            "messages": conversation,
            "max_tokens": settings.llm_max_tokens,
            "temperature": 0.2,
        }

        # Include tools in all rounds except the final forced-text round
        include_tools = tools and round_idx < max_rounds - 1
        if include_tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        logger.info(
            "POST %s  model=%s  messages=%d  total_len=%d  round=%d/%d  tools=%s",
            url, payload["model"], len(conversation), total_len,
            round_idx + 1, max_rounds, bool(include_tools),
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            logger.info("NIM response status: %d", response.status_code)
            if response.status_code != 200:
                logger.error("NIM error body: %s", response.text[:500])
            response.raise_for_status()

        response_data = response.json()
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})

        # Check for tool calls
        tool_calls = message.get("tool_calls")
        if tool_calls and include_tools:
            logger.info("LLM requested %d tool call(s) in round %d", len(tool_calls), round_idx + 1)

            # Append the assistant message with tool calls
            conversation.append(message)

            # Execute each tool call and append results
            from app.core.llm_tools import execute_tool

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    arguments = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    arguments = {}

                logger.info("Executing tool: %s(%s)", tool_name, arguments)
                tool_result = await execute_tool(
                    tool_name, arguments, user_id=user_id, db=db,
                )
                logger.info("Tool result: %s", tool_result[:200])

                conversation.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result,
                })

            # Continue the loop for the next round
            continue

        # No tool calls — parse as final response
        return parse_nemotron_response(response_data)

    # Exhausted all rounds — parse whatever we got last
    logger.warning("Tool calling loop exhausted %d rounds, parsing last response", max_rounds)
    return parse_nemotron_response(response_data)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_nemotron_response(response: dict) -> list[Correction]:
    """Parse Nemotron response into Correction objects."""
    try:
        choice = response["choices"][0]
        finish_reason = choice.get("finish_reason", "unknown")
        content = choice["message"]["content"]

        if content is None and finish_reason == "length":
            # Model used all tokens on reasoning and never produced content.
            # Log the reasoning so we can see what happened.
            reasoning = choice["message"].get("reasoning", "")
            if reasoning:
                logger.warning(
                    "LLM exhausted max_tokens on reasoning (finish_reason=length). "
                    "Reasoning (%d chars): %s",
                    len(reasoning), reasoning[:500],
                )
            else:
                logger.warning(
                    "LLM returned null content with finish_reason=length — "
                    "increase LLM_MAX_TOKENS (current: %d)",
                    settings.llm_max_tokens,
                )
            return []

        if content is None:
            logger.warning(
                "LLM returned null content — finish_reason=%s  full_choice=%s",
                finish_reason,
                str(choice)[:1000],
            )
            return []

        logger.info(
            "LLM raw response (%d chars, finish_reason=%s): %s",
            len(content), finish_reason, content[:500],
        )

        corrections = parse_json_from_llm_response(
            content=content,
            model_class=Correction,
            is_array=True
        )

        logger.info("Parsed %d corrections from LLM response", len(corrections))
        return corrections

    except (KeyError, IndexError) as e:
        logger.error("Failed to extract content from response: %s | keys=%s", e, list(response.keys()))
        return []
