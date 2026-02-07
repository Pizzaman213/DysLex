"""Error pattern repository."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import ErrorPattern

logger = logging.getLogger(__name__)


async def get_all_patterns(db: AsyncSession) -> list[ErrorPattern]:
    """Get all error patterns."""
    try:
        result = await db.execute(select(ErrorPattern))
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_all_patterns: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting all patterns: {e}")
        raise DatabaseError(f"Failed to get all patterns: {e}") from e


async def get_pattern_by_id(db: AsyncSession, pattern_id: str) -> ErrorPattern | None:
    """Get a pattern by ID."""
    try:
        result = await db.execute(select(ErrorPattern).where(ErrorPattern.id == pattern_id))
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_pattern_by_id for pattern {pattern_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting pattern {pattern_id}: {e}")
        raise DatabaseError(f"Failed to get pattern: {e}") from e


async def get_patterns_by_category(db: AsyncSession, category: str) -> list[ErrorPattern]:
    """Get patterns by category."""
    try:
        result = await db.execute(select(ErrorPattern).where(ErrorPattern.category == category))
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_patterns_by_category for category {category}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting patterns by category {category}: {e}")
        raise DatabaseError(f"Failed to get patterns by category: {e}") from e


async def create_pattern(db: AsyncSession, pattern: ErrorPattern) -> ErrorPattern:
    """Create a new error pattern."""
    try:
        db.add(pattern)
        await db.flush()
        await db.refresh(pattern)
        return pattern
    except IntegrityError as e:
        logger.error(f"Integrity error creating pattern: {e}")
        raise DuplicateRecordError("Pattern already exists") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_pattern: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating pattern: {e}")
        raise DatabaseError(f"Failed to create pattern: {e}") from e
