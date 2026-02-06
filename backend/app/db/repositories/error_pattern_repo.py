"""Error pattern repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ErrorPattern


async def get_all_patterns(db: AsyncSession) -> list[ErrorPattern]:
    """Get all error patterns."""
    result = await db.execute(select(ErrorPattern))
    return list(result.scalars().all())


async def get_pattern_by_id(db: AsyncSession, pattern_id: str) -> ErrorPattern | None:
    """Get a pattern by ID."""
    result = await db.execute(select(ErrorPattern).where(ErrorPattern.id == pattern_id))
    return result.scalar_one_or_none()


async def get_patterns_by_category(db: AsyncSession, category: str) -> list[ErrorPattern]:
    """Get patterns by category."""
    result = await db.execute(select(ErrorPattern).where(ErrorPattern.category == category))
    return list(result.scalars().all())


async def create_pattern(db: AsyncSession, pattern: ErrorPattern) -> ErrorPattern:
    """Create a new error pattern."""
    db.add(pattern)
    await db.flush()
    await db.refresh(pattern)
    return pattern
