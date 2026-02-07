"""Deprecate legacy error_profiles JSONB table.

Revision ID: 003
Revises: 002
Create Date: 2026-02-06

The error_profiles table was a JSONB cache that has been superseded by normalized tables:
- user_error_patterns (replaces patterns JSONB)
- user_confusion_pairs (replaces confusion_pairs JSONB)
- progress_snapshots (replaces achievements JSONB)

All data has been migrated to normalized tables. This migration drops the legacy table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Drop the legacy error_profiles table."""
    op.drop_table('error_profiles')


def downgrade():
    """Recreate error_profiles table if rollback needed."""
    op.create_table(
        'error_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('confusion_pairs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('achievements', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
