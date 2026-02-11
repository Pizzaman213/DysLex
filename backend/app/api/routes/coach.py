"""AI Coach chat endpoint."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import CurrentUserId, DbSession
from app.config import settings
from app.core.coach_prompts import build_coach_system_prompt
from app.middleware.rate_limiter import LLM_LIMIT, limiter
from app.models.coach import CoachChatRequest, CoachChatResponse
from app.models.envelope import success_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
@limiter.limit(LLM_LIMIT)
async def coach_chat(
    request: Request,
    body: CoachChatRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Send a message to the AI writing coach and get a reply."""
    if not settings.nvidia_nim_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI Coach is not available — no API key configured.",
        )

    # Load user error profile for personalization
    llm_context = None
    try:
        from app.core.error_profile import error_profile_service

        llm_context = await error_profile_service.build_llm_context(user_id, db)
    except Exception:
        logger.warning("Failed to load LLM context for coach", exc_info=True)

    corrections_ctx = (
        body.corrections_context.model_dump() if body.corrections_context else None
    )

    system_prompt = build_coach_system_prompt(
        llm_context=llm_context,
        writing_context=body.writing_context,
        session_stats=body.session_stats,
        corrections_context=corrections_ctx,
    )

    has_focused = (
        body.corrections_context is not None
        and body.corrections_context.focused_correction is not None
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": body.message},
    ]

    try:
        url = f"{settings.nvidia_nim_llm_url}/chat/completions"
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia_nim_llm_model,
                    "messages": messages,
                    "max_tokens": 768 if has_focused else 512,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()

        data = response.json()
        reply = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not reply:
            reply = "I'm here to help! Could you tell me a bit more about what you're working on?"

        return success_response(CoachChatResponse(reply=reply).model_dump())

    except httpx.HTTPStatusError as exc:
        logger.error("Coach LLM call failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The AI coach is temporarily unavailable. Please try again.",
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error("Coach LLM call timed out: %s", exc)
        raise HTTPException(
            status_code=504,
            detail="The AI coach took too long to respond. Please try again.",
        ) from exc
