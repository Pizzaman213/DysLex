"""Error log repository for passive learning."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import ErrorLog

logger = logging.getLogger(__name__)


async def create_error_log(
    db: AsyncSession,
    user_id: str,
    original_text: str,
    corrected_text: str,
    error_type: str,
    context: str | None = None,
    confidence: float = 0.0,
    source: str = "passive",
) -> ErrorLog:
    """Create a new error log entry."""
    try:
        error_log = ErrorLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            original_text=original_text,
            corrected_text=corrected_text,
            error_type=error_type,
            context=context,
            confidence=confidence,
            source=source,
            created_at=datetime.utcnow(),
        )

        db.add(error_log)
        await db.flush()
        return error_log
    except IntegrityError as e:
        logger.error(f"Integrity error creating error log for user {user_id}: {e}")
        raise DuplicateRecordError("Error log creation failed due to constraint violation") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_error_log: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating error log for user {user_id}: {e}")
        raise DatabaseError(f"Failed to create error log: {e}") from e


async def get_error_logs_by_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
) -> list[ErrorLog]:
    """Get error logs for a user."""
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.user_id == user_id)
            .order_by(ErrorLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_error_logs_by_user for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting error logs for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get error logs: {e}") from e


async def get_error_count_by_period(
    db: AsyncSession,
    user_id: str,
    days: int = 14,
) -> int:
    """Get total error count for a user within the last N days."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(func.count())
            .select_from(ErrorLog)
            .where(
                ErrorLog.user_id == user_id,
                ErrorLog.created_at >= cutoff,
            )
        )
        return result.scalar_one()
    except OperationalError as e:
        logger.error(f"Database connection error in get_error_count_by_period for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting error count for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get error count: {e}") from e


async def get_recent_errors_for_words(
    db: AsyncSession,
    user_id: str,
    words: list[str],
    days: int = 14,
) -> list[ErrorLog]:
    """Get recent error logs matching specific original words."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(ErrorLog).where(
                ErrorLog.user_id == user_id,
                ErrorLog.original_text.in_(words),
                ErrorLog.created_at >= cutoff,
            )
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_recent_errors_for_words for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting recent errors for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get recent errors: {e}") from e


async def delete_logs_before_date(
    db: AsyncSession,
    user_id: str,
    cutoff_date: datetime,
) -> int:
    """Delete error logs before a cutoff date.

    Returns:
        Number of logs deleted.
    """
    try:
        result = await db.execute(
            delete(ErrorLog).where(
                ErrorLog.user_id == user_id,
                ErrorLog.created_at < cutoff_date,
            )
        )
        await db.flush()
        deleted: int = result.rowcount  # type: ignore[assignment]
        logger.info(f"Deleted {deleted} logs for user {user_id} before {cutoff_date}")
        return deleted
    except OperationalError as e:
        logger.error(f"Database connection error in delete_logs_before_date for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error deleting old logs for user {user_id}: {e}")
        raise DatabaseError(f"Failed to delete old logs: {e}") from e


async def archive_old_logs(
    db: AsyncSession,
    user_id: str,
    days: int = 365,
) -> int:
    """Archive logs older than N days.

    Args:
        days: Number of days to keep. Logs older than this are deleted.

    Returns:
        Number of logs archived (deleted).
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        return await delete_logs_before_date(db, user_id, cutoff)
    except Exception as e:
        logger.error(f"Unexpected error archiving old logs for user {user_id}: {e}")
        raise DatabaseError(f"Failed to archive old logs: {e}") from e
