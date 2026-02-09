"""
Pydantic models for AI Brainstorm conversation endpoints.
"""

from typing import Literal

from pydantic import BaseModel, Field
from app.models.capture import SubIdea, ThoughtCard


class ConversationTurn(BaseModel):
    """A single turn in the brainstorm conversation."""
    role: Literal["user", "ai"] = Field(..., description="'user' or 'ai'")
    content: str = Field(..., description="Text of the turn")


class BrainstormTurnRequest(BaseModel):
    """Request body for a single brainstorm conversation turn."""
    user_utterance: str = Field(..., description="What the user just said")
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Previous conversation turns",
    )
    existing_cards: list[dict] = Field(
        default_factory=list,
        description="Current card titles+bodies for context",
    )
    transcript_so_far: str = Field(
        default="",
        description="Full accumulated transcript",
    )


class BrainstormTurnResponse(BaseModel):
    """Response from a brainstorm conversation turn."""
    reply: str = Field(..., description="AI's spoken response (1-5 sentences)")
    audio_url: str = Field(
        default="",
        description="MagpieTTS audio URL for the reply (empty if TTS unavailable)",
    )
    new_sub_ideas: list[SubIdea] = Field(
        default_factory=list,
        description="Sub-ideas extracted from this turn",
    )
    suggested_parent_card_id: str | None = Field(
        default=None,
        description="Which existing card to attach sub-ideas to",
    )
    suggested_new_card: ThoughtCard | None = Field(
        default=None,
        description="A whole new idea cluster found in this turn",
    )
