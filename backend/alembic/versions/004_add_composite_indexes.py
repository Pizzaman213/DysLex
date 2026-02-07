"""Add composite indexes for query performance.

Revision ID: 004
Revises: 003
Create Date: 2026-02-06

Adds composite indexes to speed up common query patterns:
- error_logs(user_id, created_at DESC) for time-range queries
- user_error_patterns(user_id, error_type) for type breakdown
- user_error_patterns(user_id, last_seen) for mastered pattern detection
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_error_logs_user_created",
        "error_logs",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_user_error_patterns_user_type",
        "user_error_patterns",
        ["user_id", "error_type"],
    )
    op.create_index(
        "idx_user_error_patterns_user_lastseen",
        "user_error_patterns",
        ["user_id", "last_seen"],
    )


def downgrade() -> None:
    op.drop_index("idx_user_error_patterns_user_lastseen", table_name="user_error_patterns")
    op.drop_index("idx_user_error_patterns_user_type", table_name="user_error_patterns")
    op.drop_index("idx_error_logs_user_created", table_name="error_logs")
