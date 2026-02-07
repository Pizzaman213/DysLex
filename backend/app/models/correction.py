"""Correction request/response models."""

from pydantic import BaseModel, model_validator


class Position(BaseModel):
    """Character position range within text."""

    start: int
    end: int


class Correction(BaseModel):
    """Individual correction returned by the two-tier system."""

    original: str
    correction: str
    error_type: str = "spelling"  # spelling, grammar, homophone, phonetic, subject_verb, tense, article, word_order, missing_word, run_on, clarity, style, word_choice
    position: Position | None = None
    confidence: float = 0.9
    explanation: str | None = None
    tier: str = "quick"  # "quick" | "deep"

    @model_validator(mode="before")
    @classmethod
    def remap_llm_fields(cls, data: dict) -> dict:
        """Handle LLM responses that use different field names."""
        if isinstance(data, dict):
            # Map 'suggested' -> 'correction'
            if "suggested" in data and "correction" not in data:
                data["correction"] = data.pop("suggested")
            # Map 'type' -> 'error_type'
            if "type" in data and "error_type" not in data:
                data["error_type"] = data.pop("type")
        return data


class CorrectionRequest(BaseModel):
    """Request for text corrections."""

    text: str
    context: str | None = None
    mode: str = "auto"  # "quick" | "deep" | "auto" | "document"


class CorrectionResponse(BaseModel):
    """Response containing corrections (inner data)."""

    corrections: list[Correction]
