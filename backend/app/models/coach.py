"""Pydantic models for the AI Coach chat feature."""

from pydantic import BaseModel, Field


class CorrectionDetail(BaseModel):
    """A single correction's data for coach context."""

    original: str
    suggested: str
    type: str
    explanation: str | None = None


class CorrectionsContext(BaseModel):
    """Active corrections and optionally a focused correction the user is asking about."""

    active_corrections: list[CorrectionDetail] = Field(default_factory=list)
    focused_correction: CorrectionDetail | None = None


class CoachChatRequest(BaseModel):
    """Request body for coach chat."""

    message: str = Field(..., min_length=1, max_length=2000)
    writing_context: str | None = Field(
        None,
        max_length=3000,
        description="Truncated current document text for context",
    )
    session_stats: dict | None = Field(
        None,
        description="Current session statistics (words written, time spent, etc.)",
    )
    corrections_context: CorrectionsContext | None = Field(
        None,
        description="Active corrections and focused correction for explanation",
    )


class CoachChatResponse(BaseModel):
    """Response body for coach chat."""

    reply: str
