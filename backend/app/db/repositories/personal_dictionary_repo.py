"""Repository for per-user personal dictionary."""

import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import PersonalDictionary

logger = logging.getLogger(__name__)


async def get_dictionary(
    db: AsyncSession,
    user_id: str,
) -> list[PersonalDictionary]:
    """Get all personal dictionary entries for a user."""
    try:
        result = await db.execute(
            select(PersonalDictionary)
            .where(PersonalDictionary.user_id == user_id)
            .order_by(PersonalDictionary.word)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_dictionary for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting dictionary for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get dictionary: {e}") from e


async def check_word(
    db: AsyncSession,
    user_id: str,
    word: str,
) -> bool:
    """Check if a word is in the user's personal dictionary."""
    try:
        result = await db.execute(
            select(PersonalDictionary).where(
                PersonalDictionary.user_id == user_id,
                PersonalDictionary.word == word.lower(),
            )
        )
        return result.scalar_one_or_none() is not None
    except OperationalError as e:
        logger.error(f"Database connection error in check_word for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error checking word for user {user_id}: {e}")
        raise DatabaseError(f"Failed to check word: {e}") from e


async def add_word(
    db: AsyncSession,
    user_id: str,
    word: str,
    source: str = "manual",
) -> PersonalDictionary:
    """Add a word to the user's personal dictionary (idempotent)."""
    try:
        normalized = word.lower().strip()

        result = await db.execute(
            select(PersonalDictionary).where(
                PersonalDictionary.user_id == user_id,
                PersonalDictionary.word == normalized,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        entry = PersonalDictionary(
            id=str(uuid.uuid4()),
            user_id=user_id,
            word=normalized,
            source=source,
            added_at=datetime.utcnow(),
        )
        db.add(entry)
        await db.flush()
        return entry
    except IntegrityError as e:
        logger.error(f"Integrity error adding word to dictionary for user {user_id}: {e}")
        raise DuplicateRecordError(f"Word '{word}' already exists in dictionary") from e
    except OperationalError as e:
        logger.error(f"Database connection error in add_word: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error adding word for user {user_id}: {e}")
        raise DatabaseError(f"Failed to add word: {e}") from e


async def remove_word(
    db: AsyncSession,
    user_id: str,
    word: str,
) -> bool:
    """Remove a word from the personal dictionary. Returns True if removed."""
    try:
        result = await db.execute(
            delete(PersonalDictionary).where(
                PersonalDictionary.user_id == user_id,
                PersonalDictionary.word == word.lower(),
            )
        )
        await db.flush()
        return result.rowcount > 0
    except OperationalError as e:
        logger.error(f"Database connection error in remove_word for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error removing word for user {user_id}: {e}")
        raise DatabaseError(f"Failed to remove word: {e}") from e
