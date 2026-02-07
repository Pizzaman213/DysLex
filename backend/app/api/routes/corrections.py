"""Text correction endpoints — the heart of DysLex AI."""

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import CurrentUserId, DbSession
from app.core.llm_orchestrator import auto_route, deep_only, document_review, quick_only
from app.middleware.rate_limiter import LLM_LIMIT, limiter
from app.models.correction import CorrectionRequest
from app.models.envelope import success_response
from app.services.nemotron_client import DeepAnalysisError

router = APIRouter()


def _correction_meta(
    corrections: list,
    tier: str,
    start_ns: float,
    profile_loaded: bool,
) -> dict:
    """Build standard meta dict for correction responses."""
    elapsed_ms = round((time.perf_counter() - start_ns) * 1000, 2)
    quick_count = sum(1 for c in corrections if c.tier == "quick")
    deep_count = sum(1 for c in corrections if c.tier == "deep")
    return {
        "request_id": str(uuid.uuid4()),
        "processing_time_ms": elapsed_ms,
        "tier_used": tier,
        "quick_corrections": quick_count,
        "deep_corrections": deep_count,
        "profile_loaded": profile_loaded,
    }


@router.post("/quick")
@limiter.limit(LLM_LIMIT)
async def quick_correction_endpoint(
    request: Request,
    body: CorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Quick local-model correction only (Tier 1)."""
    start = time.perf_counter()
    corrections = await quick_only(text=body.text, user_id=user_id, db=db)
    meta = _correction_meta(corrections, "quick", start, profile_loaded=True)
    return success_response(
        {"corrections": [c.model_dump() for c in corrections]},
        **meta,
    )


@router.post("/deep")
@limiter.limit(LLM_LIMIT)
async def deep_correction_endpoint(
    request: Request,
    body: CorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Full LLM-powered deep analysis only (Tier 2)."""
    start = time.perf_counter()
    try:
        corrections = await deep_only(
            text=body.text, user_id=user_id, context=body.context, db=db,
            raise_on_error=True,
        )
    except DeepAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    meta = _correction_meta(corrections, "deep", start, profile_loaded=True)
    return success_response(
        {"corrections": [c.model_dump() for c in corrections]},
        **meta,
    )


@router.post("/auto")
@limiter.limit(LLM_LIMIT)
async def auto_correction_endpoint(
    request: Request,
    body: CorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Primary endpoint — auto-routes based on confidence threshold."""
    start = time.perf_counter()
    corrections = await auto_route(
        text=body.text, user_id=user_id, context=body.context, db=db,
    )
    tier = "auto"
    meta = _correction_meta(corrections, tier, start, profile_loaded=True)
    return success_response(
        {"corrections": [c.model_dump() for c in corrections]},
        **meta,
    )


@router.post("/document")
@limiter.limit(LLM_LIMIT)
async def document_correction_endpoint(
    request: Request,
    body: CorrectionRequest,
    user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    """Full-document deep review (Tier 2 only)."""
    start = time.perf_counter()
    try:
        corrections = await document_review(
            text=body.text, user_id=user_id, context=body.context, db=db,
        )
    except DeepAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    meta = _correction_meta(corrections, "deep", start, profile_loaded=True)
    return success_response(
        {"corrections": [c.model_dump() for c in corrections]},
        **meta,
    )
