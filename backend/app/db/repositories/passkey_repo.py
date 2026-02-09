"""Repository for WebAuthn passkey credential operations."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PasskeyCredential

logger = logging.getLogger(__name__)


async def create_passkey_credential(db: AsyncSession, credential: PasskeyCredential) -> PasskeyCredential:
    """Persist a new passkey credential."""
    db.add(credential)
    await db.flush()
    await db.refresh(credential)
    return credential


async def get_credentials_by_user_id(db: AsyncSession, user_id: str) -> list[PasskeyCredential]:
    """Return all passkey credentials for a user."""
    result = await db.execute(
        select(PasskeyCredential).where(PasskeyCredential.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_credential_by_credential_id(db: AsyncSession, credential_id: bytes) -> PasskeyCredential | None:
    """Look up a passkey credential by its WebAuthn credential ID."""
    result = await db.execute(
        select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
    )
    return result.scalar_one_or_none()


async def update_credential_sign_count(db: AsyncSession, credential_id: bytes, new_count: int) -> None:
    """Update the sign count and last-used timestamp after a successful authentication."""
    result = await db.execute(
        select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id)
    )
    cred = result.scalar_one_or_none()
    if cred:
        cred.sign_count = new_count
        cred.last_used_at = datetime.utcnow()
        await db.flush()
