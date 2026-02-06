"""Progress tracking models."""

from pydantic import BaseModel


class ProgressStats(BaseModel):
    """User progress statistics."""

    overall_score: int
    words_written: int
    corrections_accepted: int
    patterns_mastered: int
    streak_days: int
    achievements: list[dict]


class DailyProgress(BaseModel):
    """Daily progress entry."""

    date: str
    words_written: int
    corrections_made: int
    accuracy_score: float
