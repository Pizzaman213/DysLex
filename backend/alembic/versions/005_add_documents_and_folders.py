"""Add documents and folders tables.

Revision ID: 005
Revises: 004
Create Date: 2026-02-07

Adds document and folder persistence so user work survives across sessions
and devices. The frontend continues using localStorage as the immediate
source of truth and syncs to these tables in the background.

Tables:
- folders: User folders for organising documents.
- documents: User documents with content, mode, and optional folder FK.

Key design decisions:
- VARCHAR(36) primary keys match client-generated IDs for offline-first sync.
- folder_id ON DELETE SET NULL so orphaned docs move to root instead of being lost.
- user_id ON DELETE CASCADE for GDPR compliance.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create folders table first (documents FK references it)
    # Use UUID to match the existing users.id column type
    op.create_table(
        "folders",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_folders_user_id", "folders", ["user_id"])

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "folder_id",
            UUID(as_uuid=False),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            server_default="Untitled Document",
        ),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("mode", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_documents_user_id", "documents", ["user_id"])
    op.create_index(
        "idx_documents_user_folder", "documents", ["user_id", "folder_id"]
    )
    op.create_index(
        "idx_documents_user_folder_sort",
        "documents",
        ["user_id", "folder_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("idx_documents_user_folder_sort", table_name="documents")
    op.drop_index("idx_documents_user_folder", table_name="documents")
    op.drop_index("idx_documents_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("idx_folders_user_id", table_name="folders")
    op.drop_table("folders")
