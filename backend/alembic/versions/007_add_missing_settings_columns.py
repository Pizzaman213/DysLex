"""Add missing settings columns for writing modes, AI features, tools, and appearance.

Revision ID: 007
Revises: 006
Create Date: 2026-02-08

The frontend sends 28 settings fields but only 15 had database columns.
This migration adds the 13 missing columns so all user settings persist
across sessions and devices.
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Writing Modes
    op.add_column("user_settings", sa.Column("mind_map_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user_settings", sa.Column("draft_mode_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user_settings", sa.Column("polish_mode_enabled", sa.Boolean, nullable=False, server_default="true"))

    # AI Features
    op.add_column("user_settings", sa.Column("passive_learning", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user_settings", sa.Column("ai_coaching", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user_settings", sa.Column("inline_corrections", sa.Boolean, nullable=False, server_default="true"))

    # Tools
    op.add_column("user_settings", sa.Column("progress_tracking", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("user_settings", sa.Column("read_aloud", sa.Boolean, nullable=False, server_default="true"))

    # Appearance
    op.add_column("user_settings", sa.Column("page_type", sa.String(20), nullable=False, server_default="a4"))
    op.add_column("user_settings", sa.Column("view_mode", sa.String(20), nullable=False, server_default="paper"))
    op.add_column("user_settings", sa.Column("zoom", sa.Integer, nullable=False, server_default="100"))
    op.add_column("user_settings", sa.Column("show_zoom", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("user_settings", sa.Column("page_numbers", sa.Boolean, nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("user_settings", "page_numbers")
    op.drop_column("user_settings", "show_zoom")
    op.drop_column("user_settings", "zoom")
    op.drop_column("user_settings", "view_mode")
    op.drop_column("user_settings", "page_type")
    op.drop_column("user_settings", "read_aloud")
    op.drop_column("user_settings", "progress_tracking")
    op.drop_column("user_settings", "inline_corrections")
    op.drop_column("user_settings", "ai_coaching")
    op.drop_column("user_settings", "passive_learning")
    op.drop_column("user_settings", "polish_mode_enabled")
    op.drop_column("user_settings", "draft_mode_enabled")
    op.drop_column("user_settings", "mind_map_enabled")
