"""
API routes for AI Brainstorm conversation.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.brainstorm import BrainstormTurnRequest, BrainstormTurnResponse
from app.services.brainstorm_service import brainstorm_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/turn", response_model=BrainstormTurnResponse)
async def brainstorm_turn_endpoint(
    request: BrainstormTurnRequest,
) -> BrainstormTurnResponse:
    """
    Process a single brainstorm conversation turn.

    Accepts the user's latest utterance plus conversation history,
    returns AI reply and any extracted sub-ideas or new cards.
    """
    logger.info(
        "Brainstorm turn request: utterance=%d chars, history=%d turns, "
        "cards=%d, transcript=%d chars",
        len(request.user_utterance),
        len(request.conversation_history),
        len(request.existing_cards),
        len(request.transcript_so_far),
    )

    if not request.user_utterance.strip():
        logger.warning("Brainstorm turn rejected: empty utterance")
        raise HTTPException(status_code=400, detail="User utterance cannot be empty")

    try:
        result = await brainstorm_service.process_turn(
            user_utterance=request.user_utterance,
            conversation_history=[
                {"role": t.role, "content": t.content}
                for t in request.conversation_history
            ],
            existing_cards=request.existing_cards,
            transcript_so_far=request.transcript_so_far,
        )
        logger.info("Brainstorm turn success: reply=%d chars", len(result.reply))
        return result

    except Exception as e:
        logger.error(
            "Brainstorm turn endpoint error: %s: %s",
            type(e).__name__, e, exc_info=True,
        )
        detail = f"Brainstorm failed: {e}" if settings.dev_mode else "Brainstorm failed"
        raise HTTPException(status_code=500, detail=detail)
