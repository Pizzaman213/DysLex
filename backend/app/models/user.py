"""User models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


def _to_camel(name: str) -> str:
    """Convert snake_case to camelCase for JSON serialization."""
    parts = name.split("_")
    return parts[0] + "".join(w.title() for w in parts[1:])


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    name: str | None = None


class UserSettings(BaseModel):
    """User-configurable settings."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    # General
    language: str = "en"

    # Writing Modes
    mind_map_enabled: bool = True
    draft_mode_enabled: bool = True
    polish_mode_enabled: bool = True

    # AI Features
    passive_learning: bool = True
    ai_coaching: bool = True
    inline_corrections: bool = True

    # Tools
    progress_tracking: bool = True
    read_aloud: bool = True

    # Appearance
    theme: str = "cream"
    font: str = "OpenDyslexic"
    page_type: str = "a4"
    view_mode: str = "paper"
    zoom: int = 100
    show_zoom: bool = False
    page_numbers: bool = True
    font_size: int = 18
    line_spacing: float = 1.75
    letter_spacing: float = 0.05

    # Accessibility
    voice_enabled: bool = True
    auto_correct: bool = True
    focus_mode: bool = False
    tts_speed: float = 1.0
    correction_aggressiveness: int = 50

    # Privacy
    anonymized_data_collection: bool = False
    cloud_sync: bool = False

    # Advanced
    developer_mode: bool = False

    # LLM Provider
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key_encrypted: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def llm_api_key_configured(self) -> bool:
        return bool(self.llm_api_key_encrypted)


class UserSettingsUpdate(BaseModel):
    """Partial update for user settings."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    # General
    language: str | None = None

    # Writing Modes
    mind_map_enabled: bool | None = None
    draft_mode_enabled: bool | None = None
    polish_mode_enabled: bool | None = None

    # AI Features
    passive_learning: bool | None = None
    ai_coaching: bool | None = None
    inline_corrections: bool | None = None

    # Tools
    progress_tracking: bool | None = None
    read_aloud: bool | None = None

    # Appearance
    theme: str | None = None
    font: str | None = None
    page_type: str | None = None
    view_mode: str | None = None
    zoom: int | None = None
    show_zoom: bool | None = None
    page_numbers: bool | None = None
    font_size: int | None = None
    line_spacing: float | None = None
    letter_spacing: float | None = None

    # Accessibility
    voice_enabled: bool | None = None
    auto_correct: bool | None = None
    focus_mode: bool | None = None
    tts_speed: float | None = None
    correction_aggressiveness: int | None = None

    # Privacy
    anonymized_data_collection: bool | None = None
    cloud_sync: bool | None = None

    # Advanced
    developer_mode: bool | None = None

    # LLM Provider
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None  # write-only plaintext, encrypted before storage


class User(UserBase):
    """User response schema."""

    id: str

    class Config:
        from_attributes = True


class UserExport(BaseModel):
    """Full data export for GDPR compliance."""

    user: User
    error_profile: dict | None = None
    error_logs: list[dict] = []
    settings: UserSettings | None = None
