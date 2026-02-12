"""Repository for user settings."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import UserSettings

logger = logging.getLogger(__name__)


async def get_settings_by_user_id(db: AsyncSession, user_id: str) -> UserSettings | None:
    """Get settings for a user by user ID.

    Args:
        db: Database session
        user_id: User ID to fetch settings for

    Returns:
        UserSettings if found, None otherwise
    """
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_settings_by_user_id for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting settings for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get settings: {e}") from e


async def create_default_settings(db: AsyncSession, user_id: str) -> UserSettings:
    """Create default settings for a new user.

    Args:
        db: Database session
        user_id: User ID to create settings for

    Returns:
        Created UserSettings instance
    """
    try:
        settings = UserSettings(
            id=str(uuid.uuid4()),
            user_id=user_id,
            # All defaults are defined in the model
        )
        db.add(settings)
        await db.flush()
        return settings
    except IntegrityError as e:
        logger.error(f"Duplicate settings for user {user_id}: {e}")
        raise DuplicateRecordError(f"Settings for user {user_id} already exist") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_default_settings: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating settings for user {user_id}: {e}")
        raise DatabaseError(f"Failed to create settings: {e}") from e


async def update_settings(
    db: AsyncSession,
    user_id: str,
    updates: dict,
) -> UserSettings | None:
    """Update settings for a user.

    Args:
        db: Database session
        user_id: User ID to update settings for
        updates: Dictionary of fields to update

    Returns:
        Updated UserSettings if found, None otherwise
    """
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            return None

        # Handle API key encryption before storage
        if "llm_api_key" in updates:
            raw_key = updates.pop("llm_api_key")
            if raw_key:
                from app.utils.encryption import encrypt_api_key
                updates["llm_api_key_encrypted"] = encrypt_api_key(raw_key)
            else:
                updates["llm_api_key_encrypted"] = None

        # Update only the provided fields
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await db.flush()
        return settings
    except OperationalError as e:
        logger.error(f"Database connection error in update_settings for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error updating settings for user {user_id}: {e}")
        raise DatabaseError(f"Failed to update settings: {e}") from e


async def get_or_create_settings(db: AsyncSession, user_id: str) -> UserSettings:
    """Get settings for a user, creating defaults if they don't exist.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        UserSettings instance
    """
    settings = await get_settings_by_user_id(db, user_id)
    if not settings:
        settings = await create_default_settings(db, user_id)
    return settings
