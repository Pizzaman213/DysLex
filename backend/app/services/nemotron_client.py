"""Nemotron client for deep text analysis (Tier 2)."""

import asyncio
import hashlib
import json
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from app.core.prompt_builder import (
    build_correction_prompt,
    build_correction_prompt_v2,
    build_system_prompt_v2,
    build_user_message,
)
from app.models.correction import Correction, Position
from app.models.error_log import LLMContext
from app.services.llm_client import LLMProviderConfig, get_system_default_config, get_user_llm_config
from app.services.redis_client import cache_get, cache_set
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

    # Resolve per-user or system LLM provider config
    if db is not None:
        llm_config = await get_user_llm_config(user_id, db)
    else:
        llm_config = get_system_default_config()

    logger.info("Provider: %s | Model: %s", llm_config.provider.value, llm_config.model)
    logger.info("API URL: %s", llm_config.base_url)
    logger.info("API key configured: %s", bool(llm_config.api_key))
    logger.info("User: %s | Text length: %d chars", user_id, len(text))

    # --- Redis response cache ---
    cache_key = _build_cache_key(user_id, text, context)
    cached = await cache_get(cache_key)
    if cached is not None:
        try:
            corrections = [Correction(**c) for c in cached]
            logger.info("Deep analysis cache HIT (%d corrections)", len(corrections))
            return corrections
        except Exception:
            logger.debug("Cache value unparseable, proceeding with fresh analysis")

    # Providers that require an API key (Ollama does not)
    needs_key = llm_config.provider.value != "ollama"
    if needs_key and not llm_config.api_key:
        logger.error("No API key — aborting deep analysis (provider=%s)", llm_config.provider.value)
        if raise_on_error:
            raise DeepAnalysisError(
                f"API key is not configured for {llm_config.provider.value}. "
                "Set it in Settings > AI Provider or via environment variables."
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

    # Pre-resolve static tool lookups (dictionary + confusion pairs)
    # so the LLM doesn't waste API round-trips calling them as tools
    pre_resolved_data: dict | None = None
    if settings.llm_tool_calling_enabled:
        from app.core.llm_tools import pre_resolve_static_lookups
        pre_resolved_data = pre_resolve_static_lookups(text)
        n_unknown = len(pre_resolved_data.get("unknown_words", []))
        n_pairs = len(pre_resolved_data.get("relevant_confusion_pairs", []))
        logger.info("Pre-resolved: %d unknown words, %d confusion pairs", n_unknown, n_pairs)

    # --- chunk the text (with sentence overlap at boundaries) ----------
    overlap_chunks = _split_into_chunks_with_overlap(text, _MAX_CHUNK_CHARS)
    logger.info("Split text into %d chunk(s) (with overlap)", len(overlap_chunks))

    # Build the system message ONCE (it's identical for every chunk)
    # Pass full text as filter_text so profile entries are trimmed to relevant ones
    system_msg: str | None = None
    if llm_context is not None:
        system_msg = build_system_prompt_v2(
            llm_context, context,
            filter_text=text,
            pre_resolved_data=pre_resolved_data,
        )

    # Build one set of messages per chunk
    # Each entry is (messages_list, doc_offset, overlap_chars)
    chunk_messages: list[tuple[list[dict], int, int]] = []
    for chunk_text, doc_offset, overlap_chars in overlap_chunks:
        if system_msg is not None:
            user_msg = build_user_message(chunk_text, context)
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
            prompt = build_correction_prompt(chunk_text, user_patterns, confusion_pairs, context)
            messages = [{"role": "user", "content": prompt}]
        total_len = sum(len(m["content"]) for m in messages)
        chunk_messages.append((messages, doc_offset, overlap_chars))
        logger.info("  Chunk doc_offset=%d  len=%d  overlap=%d  prompt_len=%d",
                     doc_offset, len(chunk_text), overlap_chars, total_len)

    # --- Prepare tool definitions if enabled ---
    tools: list[dict] | None = None
    if settings.llm_tool_calling_enabled:
        from app.core.llm_tools import TOOL_DEFINITIONS
        tools = TOOL_DEFINITIONS

    # --- call the LLM for each chunk (parallel, max 3 at a time) ------
    all_corrections: list[Correction] = []

    sem = asyncio.Semaphore(3)

    async def _analyze_chunk(
        messages: list[dict], chunk_text: str,
        doc_offset: int, overlap_chars: int,
    ) -> list[Correction]:
        async with sem:
            try:
                corrections = await _nim_circuit_breaker.call(
                    _call_nim_api(messages, tools=tools, user_id=user_id, db=db, provider_config=llm_config)
                )
                # Compute positions relative to the chunk text
                _compute_positions(chunk_text, corrections)
                # Shift positions: subtract overlap prefix, then add doc offset
                # Discard corrections that fall entirely within the overlap zone
                # (they belong to the previous chunk)
                valid: list[Correction] = []
                for c in corrections:
                    if c.position is not None:
                        adjusted_start = c.position.start - overlap_chars + doc_offset
                        adjusted_end = c.position.end - overlap_chars + doc_offset
                        if adjusted_end <= doc_offset and overlap_chars > 0:
                            # Correction is entirely in the overlap prefix — skip
                            continue
                        c.position = Position(
                            start=max(adjusted_start, doc_offset),
                            end=adjusted_end,
                        )
                    valid.append(c)
                return valid
            except CircuitBreakerOpen:
                logger.warning("Circuit breaker OPEN — skipping chunk at offset %d", doc_offset)
                if raise_on_error:
                    raise
                return []
            except Exception as exc:
                logger.warning("Chunk at offset %d failed: %s", doc_offset, exc)
                if raise_on_error:
                    raise
                return []

    tasks = []
    for messages, doc_offset, overlap_chars in chunk_messages:
        # Reconstruct chunk_text from the overlap data
        chunk_text_for_analysis = ""
        for ct, do, oc in overlap_chunks:
            if do == doc_offset and oc == overlap_chars:
                chunk_text_for_analysis = ct
                break
        tasks.append(_analyze_chunk(messages, chunk_text_for_analysis, doc_offset, overlap_chars))

    results = await asyncio.gather(*tasks, return_exceptions=raise_on_error)

    for result in results:
        if isinstance(result, BaseException):
            raise DeepAnalysisError(f"LLM analysis failed: {result}") from result
        all_corrections.extend(result)

    # Deduplicate corrections from overlapping chunk boundaries
    pre_dedup = len(all_corrections)
    all_corrections = _deduplicate_corrections(all_corrections)
    if pre_dedup != len(all_corrections):
        logger.info("Deduplicated %d -> %d corrections (overlap zone)", pre_dedup, len(all_corrections))

    logger.info("Total corrections across all chunks: %d", len(all_corrections))
    for c in all_corrections:
        logger.info("  Correction: '%s' -> '%s' [%s] pos=%s",
                    c.original, c.correction, c.error_type,
                    f"{c.position.start}-{c.position.end}" if c.position else "none")

    # Store in cache for dedup on re-submissions
    await cache_set(
        cache_key,
        [c.model_dump(mode="json") for c in all_corrections],
        ttl_seconds=settings.deep_analysis_cache_ttl,
    )
    logger.info("Deep analysis cache MISS — stored %d corrections (TTL=%ds)",
                len(all_corrections), settings.deep_analysis_cache_ttl)

    logger.info("=== DEEP ANALYSIS DONE ===")
    return all_corrections


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _build_cache_key(user_id: str, text: str, context: str | None) -> str:
    """Build a deterministic Redis key for caching deep analysis results."""
    raw = f"{user_id}:{text}:{context or ''}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"deep_cache:{digest}"


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


def _split_into_chunks_with_overlap(
    text: str, max_chars: int
) -> list[tuple[str, int, int]]:
    """Split text into chunks with sentence overlap at boundaries.

    Returns a list of (chunk_text, doc_start_offset, overlap_chars) tuples.
    ``overlap_chars`` indicates how many leading characters of this chunk
    are repeated context from the previous chunk (0 for the first chunk).
    """
    import re

    base_chunks = _split_into_chunks(text, max_chars)
    if len(base_chunks) <= 1:
        return [(base_chunks[0], 0, 0)] if base_chunks else []

    result: list[tuple[str, int, int]] = []
    offset = 0
    prev_chunk = ""

    for i, chunk in enumerate(base_chunks):
        if i == 0:
            result.append((chunk, 0, 0))
        else:
            # Extract the last sentence of the previous chunk for overlap
            sentences = re.split(r'(?<=[.!?])\s+', prev_chunk)
            last_sentence = sentences[-1] if sentences else ""
            # Cap overlap to avoid bloating the chunk
            if len(last_sentence) > 200:
                last_sentence = last_sentence[-200:]

            overlap_prefix = f"[...] {last_sentence}\n" if last_sentence else ""
            overlapped_chunk = overlap_prefix + chunk
            result.append((overlapped_chunk, offset, len(overlap_prefix)))

        offset += len(chunk)
        prev_chunk = chunk

    return result


def _deduplicate_corrections(corrections: list[Correction]) -> list[Correction]:
    """Remove duplicate corrections at the same position.

    When chunks overlap, the same correction may appear twice.
    Keep the one with higher confidence.
    """
    by_pos: dict[tuple[int, int], Correction] = {}
    no_pos: list[Correction] = []

    for c in corrections:
        if c.position is None:
            no_pos.append(c)
            continue
        key = (c.position.start, c.position.end)
        existing = by_pos.get(key)
        if existing is None or c.confidence > existing.confidence:
            by_pos[key] = c

    # Deduplicate positionless by (original, correction) keeping highest confidence
    seen: dict[tuple[str, str], Correction] = {}
    for c in no_pos:
        k = (c.original, c.correction)
        existing = seen.get(k)
        if existing is None or c.confidence > existing.confidence:
            seen[k] = c

    return list(by_pos.values()) + list(seen.values())


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
    provider_config: LLMProviderConfig | None = None,
) -> list[Correction]:
    """Call LLM API with retry on connection errors only.

    Accepts an optional *provider_config* to route the request to any
    OpenAI-compatible provider (NVIDIA NIM, Ollama, vLLM). When not
    supplied, falls back to the system default config.

    When *tools* is provided and tool calling is enabled, runs a
    conversation loop: if the model returns tool_calls instead of content,
    execute them and feed results back, up to ``llm_tool_calling_max_rounds``.
    """
    cfg = provider_config or get_system_default_config()
    url = f"{cfg.base_url}/chat/completions"

    # Work on a mutable copy of the conversation
    conversation = list(messages)
    max_rounds = settings.llm_tool_calling_max_rounds if tools else 1

    response_data: dict = {}
    for round_idx in range(max_rounds):
        total_len = sum(len(m.get("content", "") or "") for m in conversation)
        payload: dict = {
            "model": cfg.model,
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

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
            response = await client.post(url, headers=headers, json=payload)
            logger.info("LLM response status: %d", response.status_code)
            if response.status_code != 200:
                logger.error("LLM error body: %s", response.text[:500])
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
