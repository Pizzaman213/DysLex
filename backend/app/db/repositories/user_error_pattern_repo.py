"""Repository for per-user error pattern tracking."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import UserErrorPattern

logger = logging.getLogger(__name__)


async def get_profile_data(
    db: AsyncSession,
    user_id: str,
    top_limit: int = 20,
    mastered_days: int = 14,
) -> dict:
    """Fetch all patterns in one query, split into top/mastered/total in Python.

    Returns dict with keys: top_patterns, mastered_patterns, total_count, type_counts
    """
    try:
        result = await db.execute(
            select(UserErrorPattern)
            .where(UserErrorPattern.user_id == user_id)
            .order_by(UserErrorPattern.frequency.desc())
        )
        all_patterns = list(result.scalars().all())

        cutoff = datetime.now(timezone.utc) - timedelta(days=mastered_days)

        top_patterns = all_patterns[:top_limit]
        mastered_patterns = [p for p in all_patterns if p.last_seen < cutoff]
        total_count = len(all_patterns)

        # Compute type counts in Python
        type_totals: dict[str, int] = {}
        for p in all_patterns:
            et = p.error_type or "other"
            type_totals[et] = type_totals.get(et, 0) + p.frequency

        return {
            "top_patterns": top_patterns,
            "mastered_patterns": mastered_patterns,
            "total_count": total_count,
            "type_counts": list(type_totals.items()),
        }
    except OperationalError as e:
        logger.error(f"Database connection error in get_profile_data for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in get_profile_data for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get profile data: {e}") from e


async def get_top_patterns(
    db: AsyncSession,
    user_id: str,
    limit: int = 20,
) -> list[UserErrorPattern]:
    """Get top N most frequent error patterns for a user."""
    try:
        result = await db.execute(
            select(UserErrorPattern)
            .where(UserErrorPattern.user_id == user_id)
            .order_by(UserErrorPattern.frequency.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_top_patterns for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting top patterns for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get top patterns: {e}") from e


async def upsert_pattern(
    db: AsyncSession,
    user_id: str,
    misspelling: str,
    correction: str,
    error_type: str,
    language_code: str = "en",
) -> UserErrorPattern:
    """Insert or increment frequency for a user's error pattern."""
    try:
        result = await db.execute(
            select(UserErrorPattern).where(
                UserErrorPattern.user_id == user_id,
                UserErrorPattern.misspelling == misspelling,
                UserErrorPattern.correction == correction,
            )
        )
        pattern = result.scalar_one_or_none()

        if pattern is not None:
            pattern.frequency += 1
            pattern.last_seen = datetime.now(timezone.utc)
            if error_type:
                pattern.error_type = error_type
            await db.flush()
            return pattern

        pattern = UserErrorPattern(
            id=str(uuid.uuid4()),
            user_id=user_id,
            misspelling=misspelling,
            correction=correction,
            error_type=error_type,
            frequency=1,
            language_code=language_code,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )
        db.add(pattern)
        await db.flush()
        return pattern
    except IntegrityError as e:
        logger.error(f"Integrity error upserting pattern for user {user_id}: {e}")
        raise DuplicateRecordError("Pattern upsert failed due to constraint violation") from e
    except OperationalError as e:
        logger.error(f"Database connection error in upsert_pattern: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error upserting pattern for user {user_id}: {e}")
        raise DatabaseError(f"Failed to upsert pattern: {e}") from e


async def get_error_type_counts(
    db: AsyncSession,
    user_id: str,
) -> list[tuple[str, int]]:
    """Get aggregated error counts grouped by error_type."""
    try:
        result = await db.execute(
            select(
                UserErrorPattern.error_type,
                func.sum(UserErrorPattern.frequency).label("total"),
            )
            .where(UserErrorPattern.user_id == user_id)
            .group_by(UserErrorPattern.error_type)
        )
        return [(row[0], row[1]) for row in result.all()]
    except OperationalError as e:
        logger.error(f"Database connection error in get_error_type_counts for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting error type counts for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get error type counts: {e}") from e


async def get_mastered_patterns(
    db: AsyncSession,
    user_id: str,
    days_threshold: int = 14,
) -> list[UserErrorPattern]:
    """Get patterns not seen in the last N days (considered mastered)."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        result = await db.execute(
            select(UserErrorPattern).where(
                UserErrorPattern.user_id == user_id,
                UserErrorPattern.last_seen < cutoff,
            )
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_mastered_patterns for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting mastered patterns for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get mastered patterns: {e}") from e


async def mark_pattern_improving(
    db: AsyncSession,
    pattern_id: str,
    improving: bool,
) -> None:
    """Set the improving flag on a pattern."""
    try:
        await db.execute(
            update(UserErrorPattern)
            .where(UserErrorPattern.id == pattern_id)
            .values(improving=improving)
        )
        await db.flush()
    except OperationalError as e:
        logger.error(f"Database connection error in mark_pattern_improving for pattern {pattern_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error marking pattern {pattern_id} as improving: {e}")
        raise DatabaseError(f"Failed to mark pattern improving: {e}") from e


async def bulk_mark_improving(
    db: AsyncSession,
    pattern_ids: list[str],
    improving: bool,
) -> None:
    """Set the improving flag on multiple patterns at once."""
    if not pattern_ids:
        return
    try:
        await db.execute(
            update(UserErrorPattern)
            .where(UserErrorPattern.id.in_(pattern_ids))
            .values(improving=improving)
        )
        await db.flush()
    except OperationalError as e:
        logger.error(f"Database connection error in bulk_mark_improving: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in bulk_mark_improving: {e}")
        raise DatabaseError(f"Failed to bulk mark improving: {e}") from e


async def count_patterns_since(
    db: AsyncSession,
    user_id: str,
    since: datetime,
) -> int:
    """Count patterns where last_seen >= *since* for a given user."""
    try:
        result = await db.execute(
            select(func.count()).select_from(UserErrorPattern).where(
                UserErrorPattern.user_id == user_id,
                UserErrorPattern.last_seen >= since,
            )
        )
        return result.scalar_one()
    except OperationalError as e:
        logger.error(f"Database connection error in count_patterns_since for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in count_patterns_since for user {user_id}: {e}")
        raise DatabaseError(f"Failed to count patterns since: {e}") from e


async def get_pattern_count(
    db: AsyncSession,
    user_id: str,
) -> int:
    """Get total number of distinct error patterns for a user."""
    try:
        result = await db.execute(
            select(func.count()).select_from(UserErrorPattern).where(
                UserErrorPattern.user_id == user_id,
            )
        )
        return result.scalar_one()
    except OperationalError as e:
        logger.error(f"Database connection error in get_pattern_count for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting pattern count for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get pattern count: {e}") from e
