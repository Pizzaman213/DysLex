"""Add LLM provider settings columns to user_settings.

Revision ID: 009
Revises: 008
Create Date: 2026-02-12
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("llm_provider", sa.String(20), nullable=True))
    op.add_column("user_settings", sa.Column("llm_base_url", sa.String(500), nullable=True))
    op.add_column("user_settings", sa.Column("llm_model", sa.String(200), nullable=True))
    op.add_column("user_settings", sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "llm_api_key_encrypted")
    op.drop_column("user_settings", "llm_model")
    op.drop_column("user_settings", "llm_base_url")
    op.drop_column("user_settings", "llm_provider")
