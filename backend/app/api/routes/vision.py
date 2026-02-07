"""Vision endpoints for image-based idea extraction."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models.capture import ExtractIdeasResponse
from app.services.vision_extraction_service import vision_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_BASE64_SIZE = 10 * 1024 * 1024  # ~10MB base64 (roughly 7.5MB raw image)


class VisionExtractRequest(BaseModel):
    """Request to extract ideas from an image."""
    image_base64: str = Field(..., description="Base64-encoded image data (no data URI prefix)")
    mime_type: str = Field(default="image/jpeg", description="MIME type of the image")
    hint: str | None = Field(default=None, description="Optional hint about image contents")


@router.post("/extract-ideas", response_model=ExtractIdeasResponse)
async def extract_ideas_from_image(req: VisionExtractRequest) -> ExtractIdeasResponse:
    """Extract idea cards from an image using Cosmos Reason2 8B vision model."""
    if len(req.image_base64) > MAX_BASE64_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum base64 size is {MAX_BASE64_SIZE // (1024 * 1024)}MB.",
        )

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if req.mime_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{req.mime_type}'. Allowed: {', '.join(sorted(allowed_types))}",
        )

    cards, topic = await vision_extraction_service.extract_ideas_from_image(
        image_base64=req.image_base64,
        mime_type=req.mime_type,
        user_hint=req.hint,
    )

    return ExtractIdeasResponse(cards=cards, topic=topic)
