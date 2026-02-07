"""Progress repository for dashboard queries."""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, literal_column, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError
from app.db.models import ErrorLog

logger = logging.getLogger(__name__)


def _to_isoformat(value: Any) -> str:
    """Convert a datetime or string to ISO format string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.isoformat()


def _to_date(value: Any) -> "datetime.date | None":
    """Convert a date string or date object to a date object."""
    if value is None:
        return None
    if isinstance(value, str):
        from datetime import date as _date
        return _date.fromisoformat(value)
    if isinstance(value, datetime):
        return value.date()
    return value


async def get_error_frequency_by_week(
    db: AsyncSession, user_id: str, weeks: int = 12
) -> list[dict[str, Any]]:
    """Get weekly error counts for the last N weeks.

    Uses date_trunc('week', timestamp) to group errors by week boundaries (Monday).
    Excludes self-corrections to focus on AI-detected errors.

    Args:
        db: Database session
        user_id: User ID to query
        weeks: Number of weeks back to query (default 12)

    Returns:
        List of dicts with week_start (ISO string) and total_errors (int)
    """
    try:
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)

        week_col = func.date_trunc("week", ErrorLog.created_at)
        query = (
            select(
                week_col.label("week_start"),
                func.count(ErrorLog.id).label("total_errors"),
            )
            .where(ErrorLog.user_id == user_id)
            .where(ErrorLog.created_at >= cutoff)
            .where(ErrorLog.error_type != "self-correction")
            .group_by(week_col)
            .order_by(literal_column("week_start").asc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "week_start": _to_isoformat(row.week_start),
                "total_errors": row.total_errors,
            }
            for row in rows
        ]
    except OperationalError as e:
        logger.error(f"Database connection error in get_error_frequency_by_week for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting error frequency for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get error frequency: {e}") from e


async def get_error_breakdown_by_type(
    db: AsyncSession, user_id: str, weeks: int = 12
) -> list[dict[str, Any]]:
    """Get error counts by type per week.

    Groups errors by week and error_type, then maps to standard categories
    (spelling, grammar, confusion, phonetic). Provides time-series data for
    the Progress Dashboard charts.

    Args:
        db: Database session
        user_id: User ID to query
        weeks: Number of weeks back to query (default 12)

    Returns:
        List of dicts with week_start and counts for each error type category
    """
    try:
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)

        week_col = func.date_trunc("week", ErrorLog.created_at)
        query = (
            select(
                week_col.label("week_start"),
                ErrorLog.error_type,
                func.count(ErrorLog.id).label("count"),
            )
            .where(ErrorLog.user_id == user_id)
            .where(ErrorLog.created_at >= cutoff)
            .where(ErrorLog.error_type != "self-correction")
            .group_by(week_col, ErrorLog.error_type)
            .order_by(literal_column("week_start").asc())
        )

        result = await db.execute(query)
        rows = result.all()

        # Group by week
        weeks_dict: dict[str, dict[str, int]] = {}
        for row in rows:
            week_key = _to_isoformat(row.week_start)
            if week_key not in weeks_dict:
                weeks_dict[week_key] = {
                    "week_start": week_key,
                    "spelling": 0,
                    "grammar": 0,
                    "confusion": 0,
                    "phonetic": 0,
                }

            # Map error types to standard categories
            error_type = row.error_type
            if error_type in ["spelling", "grammar", "confusion", "phonetic"]:
                weeks_dict[week_key][error_type] = row.count

        return list(weeks_dict.values())
    except OperationalError as e:
        logger.error(f"Database connection error in get_error_breakdown_by_type for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting error breakdown for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get error breakdown: {e}") from e


async def get_top_errors(
    db: AsyncSession, user_id: str, limit: int = 10, weeks: int = 12
) -> list[dict[str, Any]]:
    """Get most frequent error pairs."""
    try:
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)

        query = (
            select(
                ErrorLog.original_text,
                ErrorLog.corrected_text,
                func.count(ErrorLog.id).label("frequency"),
            )
            .where(ErrorLog.user_id == user_id)
            .where(ErrorLog.created_at >= cutoff)
            .where(ErrorLog.error_type != "self-correction")
            .where(ErrorLog.original_text != ErrorLog.corrected_text)
            .group_by(ErrorLog.original_text, ErrorLog.corrected_text)
            .order_by(func.count(ErrorLog.id).desc())
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "original": row.original_text,
                "corrected": row.corrected_text,
                "frequency": row.frequency,
            }
            for row in rows
        ]
    except OperationalError as e:
        logger.error(f"Database connection error in get_top_errors for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting top errors for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get top errors: {e}") from e


async def get_mastered_words(
    db: AsyncSession, user_id: str, weeks: int = 4
) -> list[dict[str, Any]]:
    """Get words with 3+ self-corrections (mastered)."""
    try:
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)

        query = (
            select(
                ErrorLog.corrected_text.label("word"),
                func.count(ErrorLog.id).label("times_corrected"),
                func.max(ErrorLog.created_at).label("last_corrected"),
            )
            .where(ErrorLog.user_id == user_id)
            .where(ErrorLog.error_type == "self-correction")
            .where(ErrorLog.created_at >= cutoff)
            .group_by(ErrorLog.corrected_text)
            .having(func.count(ErrorLog.id) >= 3)
            .order_by(func.max(ErrorLog.created_at).desc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "word": row.word,
                "times_corrected": row.times_corrected,
                "last_corrected": _to_isoformat(row.last_corrected),
            }
            for row in rows
        ]
    except OperationalError as e:
        logger.error(f"Database connection error in get_mastered_words for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting mastered words for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get mastered words: {e}") from e


async def get_writing_streak(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Calculate current and longest writing streak.

    Algorithm:
    1. Get all distinct activity dates (days with error logs)
    2. Current streak: Count backwards from today while dates are consecutive
    3. Longest streak: Scan all dates, track longest consecutive run

    A "streak" counts days with at least one error log (indicating writing activity).
    Gaps of 1+ days break the streak.

    Returns:
        {
            "current_streak": int,  # Days from today backwards
            "longest_streak": int,  # Best ever consecutive days
            "last_activity": str,   # ISO date of most recent activity
        }
    """
    try:
        # Get all distinct activity dates
        query = (
            select(func.date(ErrorLog.created_at).label("activity_date"))
            .where(ErrorLog.user_id == user_id)
            .distinct()
            .order_by(func.date(ErrorLog.created_at).desc())
        )

        result = await db.execute(query)
        dates = [_to_date(row.activity_date) for row in result.all()]

        if not dates:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_activity": None,
            }

        # Calculate current streak (from today backwards)
        today = datetime.utcnow().date()
        current_streak = 0

        for i, activity_date in enumerate(dates):
            expected_date = today - timedelta(days=i)
            if activity_date == expected_date:
                current_streak += 1
            else:
                break

        # Calculate longest streak
        longest_streak = 1
        current_run = 1

        for i in range(1, len(dates)):
            diff = (dates[i - 1] - dates[i]).days
            if diff == 1:
                current_run += 1
                longest_streak = max(longest_streak, current_run)
            else:
                current_run = 1

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "last_activity": dates[0].isoformat() if dates else None,
        }
    except OperationalError as e:
        logger.error(f"Database connection error in get_writing_streak for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting writing streak for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get writing streak: {e}") from e


async def get_total_stats(db: AsyncSession, user_id: str) -> dict[str, Any]:
    """Get lifetime statistics."""
    try:
        # Total corrections
        corrections_query = select(func.count(ErrorLog.id)).where(
            ErrorLog.user_id == user_id
        )
        corrections_result = await db.execute(corrections_query)
        total_corrections = corrections_result.scalar() or 0

        # Approximate words written (count all error logs as proxy)
        # In real implementation, this would come from document stats
        words_query = select(func.count(ErrorLog.id)).where(ErrorLog.user_id == user_id)
        words_result = await db.execute(words_query)
        total_words = (words_result.scalar() or 0) * 10  # Rough estimate

        # Sessions (distinct days with activity)
        sessions_query = select(func.count(func.distinct(func.date(ErrorLog.created_at)))).where(
            ErrorLog.user_id == user_id
        )
        sessions_result = await db.execute(sessions_query)
        total_sessions = sessions_result.scalar() or 0

        return {
            "total_words": total_words,
            "total_corrections": total_corrections,
            "total_sessions": total_sessions,
        }
    except OperationalError as e:
        logger.error(f"Database connection error in get_total_stats for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting total stats for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get total stats: {e}") from e


async def get_improvement_by_error_type(
    db: AsyncSession, user_id: str, weeks: int = 12
) -> list[dict[str, Any]]:
    """Get improvement trends by error type.

    Trend Calculation Algorithm:
    1. Group error counts by error_type and week
    2. For each error type, compare first half vs second half of time period
    3. Calculate percentage change: ((recent_avg - earlier_avg) / earlier_avg) * 100
    4. Classify trend:
       - "improving" if change < -10% (errors decreasing)
       - "needs_attention" if change > +10% (errors increasing)
       - "stable" if -10% <= change <= +10%

    Args:
        db: Database session
        user_id: User ID to query
        weeks: Number of weeks back to query (default 12)

    Returns:
        List of dicts with error_type, change_percent, trend, and sparkline_data
    """
    try:
        cutoff = datetime.utcnow() - timedelta(weeks=weeks)

        # Get counts per type per week
        week_col = func.date_trunc("week", ErrorLog.created_at)
        query = (
            select(
                week_col.label("week_start"),
                ErrorLog.error_type,
                func.count(ErrorLog.id).label("count"),
            )
            .where(ErrorLog.user_id == user_id)
            .where(ErrorLog.created_at >= cutoff)
            .where(ErrorLog.error_type != "self-correction")
            .group_by(week_col, ErrorLog.error_type)
            .order_by(literal_column("week_start").asc())
        )

        result = await db.execute(query)
        rows = result.all()

        # Organize by error type
        type_data: dict[str, list[int]] = {}
        for row in rows:
            error_type = row.error_type
            if error_type not in type_data:
                type_data[error_type] = []
            type_data[error_type].append(row.count)

        # Calculate trends
        improvements = []
        for error_type, values in type_data.items():
            if len(values) < 2:
                continue

            # Calculate percentage change (recent vs earlier)
            mid_point = len(values) // 2
            earlier_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else 0
            recent_avg = sum(values[mid_point:]) / (len(values) - mid_point) if len(values) > mid_point else 0

            if earlier_avg > 0:
                change_percent = ((recent_avg - earlier_avg) / earlier_avg) * 100
            else:
                change_percent = 0

            # Determine trend
            if change_percent < -10:
                trend = "improving"
            elif change_percent > 10:
                trend = "needs_attention"
            else:
                trend = "stable"

            improvements.append({
                "error_type": error_type,
                "change_percent": round(change_percent, 1),
                "trend": trend,
                "sparkline_data": values[-8:],  # Last 8 weeks for sparkline
            })

        return improvements
    except OperationalError as e:
        logger.error(f"Database connection error in get_improvement_by_error_type for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting improvement trends for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get improvement trends: {e}") from e
