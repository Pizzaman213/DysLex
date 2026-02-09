"""SQLAlchemy ORM models."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    error_patterns: Mapped[list["UserErrorPattern"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    user_confusion_pairs: Mapped[list["UserConfusionPair"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    personal_dictionary: Mapped[list["PersonalDictionary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    progress_snapshots: Mapped[list["ProgressSnapshot"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    folders: Mapped[list["Folder"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    passkey_credentials: Mapped[list["PasskeyCredential"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    """User settings for application customization."""

    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # General
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # Writing Modes
    mind_map_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    draft_mode_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    polish_mode_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # AI Features
    passive_learning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_coaching: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inline_corrections: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Tools
    progress_tracking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    read_aloud: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Appearance
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="cream")
    font: Mapped[str] = mapped_column(String(50), nullable=False, default="OpenDyslexic")
    page_type: Mapped[str] = mapped_column(String(20), nullable=False, default="a4")
    view_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="paper")
    zoom: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    show_zoom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    page_numbers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    font_size: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
    line_spacing: Mapped[float] = mapped_column(Float, nullable=False, default=1.75)
    letter_spacing: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)

    # Accessibility
    voice_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    focus_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tts_speed: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    correction_aggressiveness: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Privacy
    anonymized_data_collection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cloud_sync: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Advanced
    developer_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="settings")


class ErrorLog(Base):
    """Log of individual errors for analysis."""

    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    was_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="passive")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="error_logs")


class UserErrorPattern(Base):
    """Per-user misspelling -> correction frequency map."""

    __tablename__ = "user_error_patterns"
    __table_args__ = (
        UniqueConstraint("user_id", "misspelling", "correction"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    misspelling: Mapped[str] = mapped_column(String(255), nullable=False)
    correction: Mapped[str] = mapped_column(String(255), nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    improving: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="error_patterns")


class UserConfusionPair(Base):
    """Per-user word confusion tracking."""

    __tablename__ = "user_confusion_pairs"
    __table_args__ = (
        UniqueConstraint("user_id", "word_a", "word_b"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_a: Mapped[str] = mapped_column(String(100), nullable=False)
    word_b: Mapped[str] = mapped_column(String(100), nullable=False)
    confusion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_confused_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="user_confusion_pairs")


class PersonalDictionary(Base):
    """Words to never flag for a user."""

    __tablename__ = "personal_dictionary"
    __table_args__ = (
        UniqueConstraint("user_id", "word"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="personal_dictionary")


class ProgressSnapshot(Base):
    """Weekly aggregated progress stats."""

    __tablename__ = "progress_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    total_words_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_corrections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_type_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    top_errors: Mapped[list] = mapped_column(JSONB, default=list)
    patterns_mastered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_patterns_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="progress_snapshots")


class ConfusionPair(Base):
    """Language-specific confusion pairs."""

    __tablename__ = "confusion_pairs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    word1: Mapped[str] = mapped_column(String(100), nullable=False)
    word2: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # homophone, reversal, etc.
    frequency: Mapped[int] = mapped_column(Integer, default=0)


class ErrorPattern(Base):
    """Known dyslexia error patterns."""

    __tablename__ = "error_patterns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    examples: Mapped[list] = mapped_column(JSONB, default=list)


class Folder(Base):
    """User folder for organising documents."""

    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="folders")
    documents: Mapped[list["Document"]] = relationship(back_populates="folder")


class Document(Base):
    """User document."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    folder_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="Untitled Document")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")
    folder: Mapped["Folder | None"] = relationship(back_populates="documents")


class PasskeyCredential(Base):
    """WebAuthn passkey credential for passwordless authentication."""

    __tablename__ = "passkey_credentials"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transports: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="passkey_credentials")
