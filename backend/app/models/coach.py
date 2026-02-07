"""Pydantic models for the AI Coach chat feature."""

from pydantic import BaseModel, Field


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


class CoachChatResponse(BaseModel):
    """Response body for coach chat."""

    reply: str
