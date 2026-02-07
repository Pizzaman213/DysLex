"""Correction request/response models."""

from pydantic import BaseModel, field_validator


class Position(BaseModel):
    """Character position range within text."""

    start: int
    end: int


class Correction(BaseModel):
    """Individual correction returned by the two-tier system."""

    original: str
    correction: str
    error_type: str = "spelling"  # spelling, grammar, confusion, phonetic
    position: Position | None = None
    confidence: float = 0.9
    explanation: str | None = None
    tier: str = "quick"  # "quick" | "deep"

    @field_validator('correction', mode='before')
    @classmethod
    def handle_suggested_field(cls, v, info):
        """Handle LLM responses using 'suggested' instead of 'correction'."""
        if v is None and info.data.get('suggested'):
            return info.data['suggested']
        return v


class CorrectionRequest(BaseModel):
    """Request for text corrections."""

    text: str
    context: str | None = None
    mode: str = "auto"  # "quick" | "deep" | "auto" | "document"


class CorrectionResponse(BaseModel):
    """Response containing corrections (inner data)."""

    corrections: list[Correction]
