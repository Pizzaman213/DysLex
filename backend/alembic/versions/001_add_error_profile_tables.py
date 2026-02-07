"""Add normalized error profile tables.

Revision ID: 001
Revises:
Create Date: 2026-02-06

This migration replaces the JSONB error_profiles table with 4 normalized tables:
- user_error_patterns: Misspelling frequency tracking per user
- user_confusion_pairs: Homophone/confusion tracking per user
- personal_dictionary: User-specific word whitelist
- progress_snapshots: Weekly aggregated statistics with JSONB breakdowns

These tables enable efficient queries for the adaptive learning system and
progress dashboard without scanning JSONB fields. All tables cascade delete
on user deletion for GDPR compliance.

Changes:
- Add source column to error_logs table (passive, quick_model, deep_model)
- Create user_error_patterns table with frequency tracking
- Create user_confusion_pairs table with alphabetical normalization
- Create personal_dictionary table with manual/auto source tracking
- Create progress_snapshots table with weekly aggregation
- Add indexes for query optimization
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source column to error_logs
    op.add_column(
        "error_logs",
        sa.Column("source", sa.String(20), server_default="passive", nullable=False),
    )
    op.create_index("idx_error_logs_source", "error_logs", ["source"])

    # user_error_patterns
    op.create_table(
        "user_error_patterns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("misspelling", sa.String(255), nullable=False),
        sa.Column("correction", sa.String(255), nullable=False),
        sa.Column("error_type", sa.String(50), nullable=False),
        sa.Column("frequency", sa.Integer, nullable=False, server_default="1"),
        sa.Column("improving", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("language_code", sa.String(10), nullable=False, server_default="en"),
        sa.Column(
            "first_seen",
            sa.DateTime,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen",
            sa.DateTime,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "misspelling", "correction"),
    )
    op.create_index(
        "idx_user_error_patterns_user_id", "user_error_patterns", ["user_id"]
    )
    op.create_index(
        "idx_user_error_patterns_user_freq",
        "user_error_patterns",
        ["user_id", sa.text("frequency DESC")],
    )

    # user_confusion_pairs
    op.create_table(
        "user_confusion_pairs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("word_a", sa.String(100), nullable=False),
        sa.Column("word_b", sa.String(100), nullable=False),
        sa.Column("confusion_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "last_confused_at",
            sa.DateTime,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "word_a", "word_b"),
    )
    op.create_index(
        "idx_user_confusion_pairs_user_id", "user_confusion_pairs", ["user_id"]
    )

    # personal_dictionary
    op.create_table(
        "personal_dictionary",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column(
            "added_at",
            sa.DateTime,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "word"),
    )
    op.create_index(
        "idx_personal_dictionary_user_id", "personal_dictionary", ["user_id"]
    )

    # progress_snapshots
    op.create_table(
        "progress_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column(
            "total_words_written", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "total_corrections", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("accuracy_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("error_type_breakdown", JSONB, server_default="{}"),
        sa.Column("top_errors", JSONB, server_default="[]"),
        sa.Column("patterns_mastered", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "new_patterns_detected", sa.Integer, nullable=False, server_default="0"
        ),
        sa.UniqueConstraint("user_id", "week_start"),
    )
    op.create_index(
        "idx_progress_snapshots_user_id", "progress_snapshots", ["user_id"]
    )
    op.create_index(
        "idx_progress_snapshots_user_week",
        "progress_snapshots",
        ["user_id", sa.text("week_start DESC")],
    )


def downgrade() -> None:
    op.drop_table("progress_snapshots")
    op.drop_table("personal_dictionary")
    op.drop_table("user_confusion_pairs")
    op.drop_table("user_error_patterns")
    op.drop_index("idx_error_logs_source", table_name="error_logs")
    op.drop_column("error_logs", "source")
