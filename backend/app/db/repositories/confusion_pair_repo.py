"""Confusion pair repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConfusionPair


async def get_pairs_by_language(db: AsyncSession, language: str) -> list[ConfusionPair]:
    """Get all confusion pairs for a language."""
    result = await db.execute(
        select(ConfusionPair).where(ConfusionPair.language == language)
    )
    return list(result.scalars().all())


async def get_pair_containing_word(
    db: AsyncSession,
    word: str,
    language: str = "en",
) -> list[ConfusionPair]:
    """Get confusion pairs containing a specific word."""
    result = await db.execute(
        select(ConfusionPair).where(
            ConfusionPair.language == language,
            (ConfusionPair.word1 == word) | (ConfusionPair.word2 == word),
        )
    )
    return list(result.scalars().all())


async def increment_pair_frequency(
    db: AsyncSession,
    pair_id: str,
) -> None:
    """Increment the frequency count for a confusion pair."""
    result = await db.execute(
        select(ConfusionPair).where(ConfusionPair.id == pair_id)
    )
    pair = result.scalar_one_or_none()
    if pair:
        pair.frequency += 1
        await db.flush()
