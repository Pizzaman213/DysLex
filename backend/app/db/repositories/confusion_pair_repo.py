"""Confusion pair repository."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError
from app.db.models import ConfusionPair

logger = logging.getLogger(__name__)


async def get_pairs_by_language(db: AsyncSession, language: str) -> list[ConfusionPair]:
    """Get all confusion pairs for a language."""
    try:
        result = await db.execute(
            select(ConfusionPair).where(ConfusionPair.language == language)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_pairs_by_language for language {language}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting pairs for language {language}: {e}")
        raise DatabaseError(f"Failed to get confusion pairs: {e}") from e


async def get_pair_containing_word(
    db: AsyncSession,
    word: str,
    language: str = "en",
) -> list[ConfusionPair]:
    """Get confusion pairs containing a specific word."""
    try:
        result = await db.execute(
            select(ConfusionPair).where(
                ConfusionPair.language == language,
                (ConfusionPair.word1 == word) | (ConfusionPair.word2 == word),
            )
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_pair_containing_word for word {word}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting pairs containing word {word}: {e}")
        raise DatabaseError(f"Failed to get pairs containing word: {e}") from e


async def increment_pair_frequency(
    db: AsyncSession,
    pair_id: str,
) -> None:
    """Increment the frequency count for a confusion pair."""
    try:
        result = await db.execute(
            select(ConfusionPair).where(ConfusionPair.id == pair_id)
        )
        pair = result.scalar_one_or_none()
        if pair:
            pair.frequency += 1
            await db.flush()
    except OperationalError as e:
        logger.error(f"Database connection error in increment_pair_frequency for pair {pair_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error incrementing frequency for pair {pair_id}: {e}")
        raise DatabaseError(f"Failed to increment pair frequency: {e}") from e
