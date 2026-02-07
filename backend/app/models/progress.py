"""Progress tracking models."""

from datetime import date

from pydantic import BaseModel, ConfigDict


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


class ProgressSnapshotResponse(BaseModel):
    """Weekly progress snapshot for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    week_start: date
    total_words_written: int
    total_corrections: int
    accuracy_score: float
    error_type_breakdown: dict
    top_errors: list
    patterns_mastered: int
    new_patterns_detected: int


# New models for dashboard

class ErrorFrequencyWeek(BaseModel):
    """Weekly error frequency."""

    week_start: str
    total_errors: int


class ErrorTypeBreakdown(BaseModel):
    """Error counts by type for a week."""

    week_start: str
    spelling: int
    grammar: int
    confusion: int
    phonetic: int


class TopError(BaseModel):
    """Most frequent error pair."""

    original: str
    corrected: str
    frequency: int


class MasteredWord(BaseModel):
    """Word that user has mastered."""

    word: str
    times_corrected: int
    last_corrected: str


class WritingStreak(BaseModel):
    """Writing streak information."""

    current_streak: int
    longest_streak: int
    last_activity: str | None


class TotalStats(BaseModel):
    """Lifetime statistics."""

    total_words: int
    total_corrections: int
    total_sessions: int


class ErrorTypeImprovement(BaseModel):
    """Improvement trend for an error type."""

    error_type: str
    change_percent: float
    trend: str  # "improving", "stable", "needs_attention"
    sparkline_data: list[int]


class ProgressDashboardResponse(BaseModel):
    """Complete dashboard data."""

    error_frequency: list[ErrorFrequencyWeek]
    error_breakdown: list[ErrorTypeBreakdown]
    top_errors: list[TopError]
    mastered_words: list[MasteredWord]
    writing_streak: WritingStreak
    total_stats: TotalStats
    improvements: list[ErrorTypeImprovement]
