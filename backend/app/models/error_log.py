"""Error profile and logging models."""

from datetime import datetime

from pydantic import BaseModel


class Pattern(BaseModel):
    """Error pattern schema."""

    id: str
    description: str
    mastered: bool
    progress: int


class ConfusionPair(BaseModel):
    """Confusion pair schema."""

    word1: str
    word2: str
    frequency: int


class Achievement(BaseModel):
    """Achievement schema."""

    id: str
    name: str
    icon: str
    earned_at: str


class ErrorProfile(BaseModel):
    """User's error profile schema."""

    user_id: str
    overall_score: int
    top_patterns: list[dict]
    confusion_pairs: list[dict]
    achievements: list[dict]


class ErrorProfileUpdate(BaseModel):
    """Schema for updating error profile."""

    patterns_to_update: list[dict] | None = None
    confusion_pairs_to_add: list[dict] | None = None


class ErrorLogEntry(BaseModel):
    """Individual error log entry."""

    id: str
    user_id: str
    original_text: str
    corrected_text: str
    error_type: str
    context: str | None
    timestamp: datetime
    was_accepted: bool | None
