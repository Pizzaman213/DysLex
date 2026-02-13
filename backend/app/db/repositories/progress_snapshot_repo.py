"""Repository for weekly progress snapshots."""

import logging
import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import ProgressSnapshot

logger = logging.getLogger(__name__)


async def get_snapshots(
    db: AsyncSession,
    user_id: str,
    weeks: int = 12,
) -> list[ProgressSnapshot]:
    """Get the last N weeks of progress snapshots."""
    try:
        result = await db.execute(
            select(ProgressSnapshot)
            .where(ProgressSnapshot.user_id == user_id)
            .order_by(ProgressSnapshot.week_start.desc())
            .limit(weeks)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_snapshots for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting snapshots for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get snapshots: {e}") from e


async def upsert_snapshot(
    db: AsyncSession,
    user_id: str,
    week_start: date,
    total_words_written: int = 0,
    total_corrections: int = 0,
    accuracy_score: float = 0.0,
    error_type_breakdown: dict[str, object] | None = None,
    top_errors: list[object] | None = None,
    patterns_mastered: int = 0,
    new_patterns_detected: int = 0,
) -> ProgressSnapshot:
    """Insert or update a weekly progress snapshot."""
    try:
        result = await db.execute(
            select(ProgressSnapshot).where(
                ProgressSnapshot.user_id == user_id,
                ProgressSnapshot.week_start == week_start,
            )
        )
        snapshot = result.scalar_one_or_none()

        if snapshot is not None:
            snapshot.total_words_written = total_words_written
            snapshot.total_corrections = total_corrections
            snapshot.accuracy_score = accuracy_score
            snapshot.error_type_breakdown = error_type_breakdown or {}
            snapshot.top_errors = top_errors or []
            snapshot.patterns_mastered = patterns_mastered
            snapshot.new_patterns_detected = new_patterns_detected
            await db.flush()
            return snapshot

        snapshot = ProgressSnapshot(
            id=str(uuid.uuid4()),
            user_id=user_id,
            week_start=week_start,
            total_words_written=total_words_written,
            total_corrections=total_corrections,
            accuracy_score=accuracy_score,
            error_type_breakdown=error_type_breakdown or {},
            top_errors=top_errors or [],
            patterns_mastered=patterns_mastered,
            new_patterns_detected=new_patterns_detected,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot
    except IntegrityError as e:
        logger.error(f"Integrity error upserting snapshot for user {user_id}: {e}")
        raise DuplicateRecordError("Snapshot upsert failed due to constraint violation") from e
    except OperationalError as e:
        logger.error(f"Database connection error in upsert_snapshot: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error upserting snapshot for user {user_id}: {e}")
        raise DatabaseError(f"Failed to upsert snapshot: {e}") from e


async def delete_snapshots_before_date(
    db: AsyncSession,
    user_id: str,
    cutoff_date: date,
) -> int:
    """Delete snapshots before cutoff date.

    Returns:
        Number of snapshots deleted.
    """
    try:
        result = await db.execute(
            delete(ProgressSnapshot).where(
                ProgressSnapshot.user_id == user_id,
                ProgressSnapshot.week_start < cutoff_date,
            )
        )
        await db.flush()
        deleted: int = result.rowcount  # type: ignore[assignment]
        logger.info(f"Deleted {deleted} snapshots for user {user_id} before {cutoff_date}")
        return deleted
    except OperationalError as e:
        logger.error(f"Database connection error in delete_snapshots_before_date for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error deleting old snapshots for user {user_id}: {e}")
        raise DatabaseError(f"Failed to delete old snapshots: {e}") from e
