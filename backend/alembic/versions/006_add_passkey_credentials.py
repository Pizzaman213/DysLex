"""Add passkey credentials table for WebAuthn authentication.

Revision ID: 006
Revises: 005
Create Date: 2026-02-08

Makes password_hash nullable on users table (passkey-only users have no
password) and creates the passkey_credentials table for storing WebAuthn
credential data per user.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow passkey-only users (no password)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)

    # Create passkey credentials table
    op.create_table(
        "passkey_credentials",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary, unique=True, nullable=False),
        sa.Column("public_key", sa.LargeBinary, nullable=False),
        sa.Column("sign_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("transports", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_passkey_credentials_user_id", "passkey_credentials", ["user_id"])
    op.create_index("idx_passkey_credentials_credential_id", "passkey_credentials", ["credential_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_passkey_credentials_credential_id", table_name="passkey_credentials")
    op.drop_index("idx_passkey_credentials_user_id", table_name="passkey_credentials")
    op.drop_table("passkey_credentials")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
