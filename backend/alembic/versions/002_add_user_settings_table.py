"""Add user_settings table.

Revision ID: 002
Revises: 001
Create Date: 2026-02-06

This migration adds the user_settings table to store per-user customization preferences.
Previously settings were hardcoded or stored in client-side localStorage. This migration
enables server-side settings persistence with the following categories:

**General Settings**:
- language: Interface language (default: en)

**Appearance Settings**:
- theme: Color theme (cream, night, blue-tint)
- font: Font family (OpenDyslexic, Atkinson Hyperlegible, Lexie Readable)
- font_size: Base font size in pixels (default: 18)
- line_spacing: Line height multiplier (default: 1.75)
- letter_spacing: Letter spacing in em units (default: 0.05)

**Accessibility Settings**:
- voice_enabled: Enable voice input (default: true)
- auto_correct: Enable automatic corrections (default: true)
- focus_mode: Dim everything except current paragraph (default: false)
- tts_speed: Text-to-speech speed multiplier (default: 1.0)
- correction_aggressiveness: How aggressively to flag errors 0-100 (default: 50)

**Privacy Settings**:
- anonymized_data_collection: Allow anonymous usage analytics (default: false)
- cloud_sync: Sync settings across devices (default: false)

**Advanced Settings**:
- developer_mode: Enable debug features (default: false)

Changes:
- Create user_settings table with 1:1 relationship to users
- Add CASCADE DELETE constraint for GDPR compliance
- Add unique constraint on user_id
- Set default values for all settings fields
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_settings
    op.create_table(
        "user_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # General
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        # Appearance
        sa.Column("theme", sa.String(20), nullable=False, server_default="cream"),
        sa.Column("font", sa.String(50), nullable=False, server_default="OpenDyslexic"),
        sa.Column("font_size", sa.Integer, nullable=False, server_default="18"),
        sa.Column("line_spacing", sa.Float, nullable=False, server_default="1.75"),
        sa.Column("letter_spacing", sa.Float, nullable=False, server_default="0.05"),
        # Accessibility
        sa.Column("voice_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("auto_correct", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("focus_mode", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tts_speed", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("correction_aggressiveness", sa.Integer, nullable=False, server_default="50"),
        # Privacy
        sa.Column("anonymized_data_collection", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cloud_sync", sa.Boolean, nullable=False, server_default="false"),
        # Advanced
        sa.Column("developer_mode", sa.Boolean, nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_user_settings_user_id", "user_settings", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_user_settings_user_id", table_name="user_settings")
    op.drop_table("user_settings")
