"""Error profile and logging models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    """User's error profile schema (legacy)."""

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


class ErrorLogCreate(BaseModel):
    """Schema for creating an error log."""

    original_text: str
    corrected_text: str
    error_type: str
    context: str | None = None
    confidence: float = 0.0
    source: str = "passive"


# ---------------------------------------------------------------------------
# New normalized profile schemas
# ---------------------------------------------------------------------------


class UserErrorPatternResponse(BaseModel):
    """Per-user error pattern for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    misspelling: str
    correction: str
    error_type: str
    frequency: int
    improving: bool
    language_code: str
    first_seen: datetime
    last_seen: datetime


class UserConfusionPairResponse(BaseModel):
    """Per-user confusion pair for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    word_a: str
    word_b: str
    confusion_count: int
    last_confused_at: datetime


class PersonalDictionaryEntry(BaseModel):
    """Personal dictionary entry for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    word: str
    source: str
    added_at: datetime


class PersonalDictionaryAdd(BaseModel):
    """Request to add a word to personal dictionary."""

    word: str
    source: str = "manual"


class ErrorTypeBreakdown(BaseModel):
    """Percentage breakdown by error type."""

    reversal: float = 0.0
    phonetic: float = 0.0
    homophone: float = 0.0
    omission: float = 0.0
    transposition: float = 0.0
    grammar: float = 0.0
    other: float = 0.0


class FullErrorProfile(BaseModel):
    """Complete assembled error profile."""

    user_id: str
    top_errors: list[UserErrorPatternResponse]
    error_type_breakdown: ErrorTypeBreakdown
    confusion_pairs: list[UserConfusionPairResponse]
    personal_dictionary: list[PersonalDictionaryEntry]
    patterns_mastered: int
    total_patterns: int
    overall_score: int


class LLMContext(BaseModel):
    """Context blob injected into every Nemotron prompt."""

    top_errors: list[dict]
    error_types: dict[str, float]
    confusion_pairs: list[dict]
    writing_level: str
    personal_dictionary: list[str]
    context_notes: list[str]
    grammar_patterns: list[dict] = []
    improvement_trends: list[dict] = []
    mastered_words: list[str] = []
    total_stats: dict | None = None
    writing_streak: dict | None = None
    recent_error_count: int | None = None
    recent_document_topics: list[str] = []
    correction_aggressiveness: int = 50
