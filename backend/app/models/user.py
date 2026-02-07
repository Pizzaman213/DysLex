"""User models."""

from pydantic import BaseModel, EmailStr


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

    # General
    language: str = "en"

    # Appearance
    theme: str = "cream"
    font: str = "OpenDyslexic"
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

    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    """Partial update for user settings."""

    # General
    language: str | None = None

    # Appearance
    theme: str | None = None
    font: str | None = None
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
