"""Correction request/response models."""

from pydantic import BaseModel


class Correction(BaseModel):
    """Individual correction."""

    original: str
    suggested: str
    type: str  # spelling, grammar, confusion, phonetic
    start: int
    end: int
    confidence: float = 0.9
    explanation: str | None = None


class CorrectionRequest(BaseModel):
    """Request for text corrections."""

    text: str
    context: str | None = None


class CorrectionResponse(BaseModel):
    """Response containing corrections."""

    corrections: list[Correction]
