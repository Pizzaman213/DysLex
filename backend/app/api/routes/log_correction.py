"""Passive learning correction logging endpoint."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import CurrentUserId, DbSession
from app.core.error_profile import error_profile_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.title() for w in parts[1:])


class LogCorrectionRequest(BaseModel):
    """Request model for logging a correction."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    original_text: str
    corrected_text: str
    error_type: str | None = None
    context: str | None = None
    confidence: float = 0.8
    source: str = "passive"


class LogCorrectionResponse(BaseModel):
    """Response model for log correction."""

    success: bool
    message: str


class LogCorrectionBatchRequest(BaseModel):
    """Request model for logging multiple corrections in batch."""

    corrections: list[LogCorrectionRequest]


class LogCorrectionBatchResponse(BaseModel):
    """Response model for batch log correction."""

    logged: int
    total: int


@router.post("", response_model=LogCorrectionResponse)
async def log_correction(
    request: LogCorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> LogCorrectionResponse:
    """Log a user's self-correction for passive learning.

    This endpoint is called automatically when the system detects
    that a user has corrected their own text. No UI interaction required.
    """
    try:
        await error_profile_service.log_error(
            user_id=user_id,
            db=db,
            original=request.original_text,
            corrected=request.corrected_text,
            error_type=request.error_type or "self-correction",
            context=request.context,
            confidence=request.confidence,
            source=request.source,
        )

        return LogCorrectionResponse(
            success=True,
            message="Correction logged successfully",
        )

    except Exception:
        # Silently fail — don't interrupt user's writing
        logger.warning("Error logging correction", exc_info=True)
        return LogCorrectionResponse(
            success=False,
            message="Failed to log correction",
        )


@router.post("/batch", response_model=LogCorrectionBatchResponse)
async def log_correction_batch(
    request: LogCorrectionBatchRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> LogCorrectionBatchResponse:
    """Log multiple user corrections in a single batch.

    This improves efficiency for passive learning by reducing API calls.
    Each correction is processed independently - failures don't affect others.
    """
    success_count = 0

    for correction in request.corrections:
        try:
            await error_profile_service.log_error(
                user_id=user_id,
                db=db,
                original=correction.original_text,
                corrected=correction.corrected_text,
                error_type=correction.error_type or "self-correction",
                context=correction.context,
                confidence=correction.confidence,
                source=correction.source,
            )
            success_count += 1
        except Exception:
            logger.warning(f"Failed to log correction in batch", exc_info=True)
            continue

    return LogCorrectionBatchResponse(
        logged=success_count,
        total=len(request.corrections),
    )
