"""
Pydantic models for Capture Mode endpoints.
"""

from typing import List
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Response from the transcription endpoint."""
    transcript: str = Field(..., description="The transcribed text from the audio file")
    language: str | None = Field(None, description="Detected language code (e.g., 'en')")
    duration: float | None = Field(None, description="Audio duration in seconds")


class SubIdea(BaseModel):
    """A sub-idea nested under a main topic."""
    id: str = Field(..., description="Unique identifier for the sub-idea")
    title: str = Field(..., description="Short title for the sub-idea")
    body: str = Field(default="", description="Detail text for the sub-idea")


class ThoughtCard(BaseModel):
    """Represents an extracted idea/thought card with optional sub-ideas."""
    id: str = Field(..., description="Unique identifier for the card")
    title: str = Field(..., description="Short title summarizing the idea")
    body: str = Field(..., description="Full text of the idea")
    sub_ideas: List[SubIdea] = Field(default_factory=list, description="Sub-ideas under this topic")


class ExtractIdeasRequest(BaseModel):
    """Request to extract idea cards from a transcript."""
    transcript: str = Field(..., description="The transcript text to analyze")


class ExtractIdeasResponse(BaseModel):
    """Response containing extracted thought cards."""
    cards: List[ThoughtCard] = Field(default_factory=list, description="List of extracted idea cards")
