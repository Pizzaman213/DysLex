"""Add index on error_logs.created_at for efficient retention cleanup.

Revision ID: 008
Revises: 007
Create Date: 2026-02-10
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_error_logs_created_at",
        "error_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_error_logs_created_at", table_name="error_logs")
