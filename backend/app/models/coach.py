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


class MindMapIdea(BaseModel):
    """A single idea from the user's mind map."""

    title: str
    body: str | None = None
    theme: str | None = None


class MindMapConnection(BaseModel):
    """A connection between two ideas in the mind map."""

    from_idea: str
    to_idea: str
    relationship: str | None = None


class MindMapContext(BaseModel):
    """Context from the user's mind map / brainstorm."""

    central_idea: str | None = None
    ideas: list[MindMapIdea] = Field(default_factory=list)
    connections: list[MindMapConnection] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


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
    mind_map_context: MindMapContext | None = Field(
        None,
        description="Ideas and connections from the user's mind map",
    )


class CoachChatResponse(BaseModel):
    """Response body for coach chat."""

    reply: str
