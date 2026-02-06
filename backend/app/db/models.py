"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    error_profile: Mapped["ErrorProfile"] = relationship(back_populates="user", uselist=False)
    error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="user")


class ErrorProfile(Base):
    """User's error profile for adaptive learning."""

    __tablename__ = "error_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    overall_score: Mapped[int] = mapped_column(Integer, default=50)
    patterns: Mapped[dict] = mapped_column(JSONB, default=dict)
    confusion_pairs: Mapped[dict] = mapped_column(JSONB, default=dict)
    achievements: Mapped[list] = mapped_column(JSONB, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="error_profile")


class ErrorLog(Base):
    """Log of individual errors for analysis."""

    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    was_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="error_logs")


class ConfusionPair(Base):
    """Language-specific confusion pairs."""

    __tablename__ = "confusion_pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    word1: Mapped[str] = mapped_column(String(100), nullable=False)
    word2: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # homophone, reversal, etc.
    frequency: Mapped[int] = mapped_column(Integer, default=0)


class ErrorPattern(Base):
    """Known dyslexia error patterns."""

    __tablename__ = "error_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    examples: Mapped[list] = mapped_column(JSONB, default=list)
