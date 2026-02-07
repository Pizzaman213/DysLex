"""Repository for per-user word confusion pair tracking."""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import UserConfusionPair

logger = logging.getLogger(__name__)


async def get_pairs_for_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
) -> list[UserConfusionPair]:
    """Get confusion pairs for a user, ordered by frequency."""
    try:
        result = await db.execute(
            select(UserConfusionPair)
            .where(UserConfusionPair.user_id == user_id)
            .order_by(UserConfusionPair.confusion_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_pairs_for_user for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting confusion pairs for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get confusion pairs: {e}") from e


async def upsert_confusion_pair(
    db: AsyncSession,
    user_id: str,
    word_a: str,
    word_b: str,
) -> UserConfusionPair:
    """Insert or increment a confusion pair (alphabetically normalized)."""
    try:
        # Alphabetical normalization so (there, their) == (their, there)
        a, b = sorted([word_a.lower(), word_b.lower()])

        result = await db.execute(
            select(UserConfusionPair).where(
                UserConfusionPair.user_id == user_id,
                UserConfusionPair.word_a == a,
                UserConfusionPair.word_b == b,
            )
        )
        pair = result.scalar_one_or_none()

        if pair is not None:
            pair.confusion_count += 1
            pair.last_confused_at = datetime.utcnow()
            await db.flush()
            return pair

        pair = UserConfusionPair(
            id=str(uuid.uuid4()),
            user_id=user_id,
            word_a=a,
            word_b=b,
            confusion_count=1,
            last_confused_at=datetime.utcnow(),
        )
        db.add(pair)
        await db.flush()
        return pair
    except IntegrityError as e:
        logger.error(f"Integrity error upserting confusion pair for user {user_id}: {e}")
        raise DuplicateRecordError("Confusion pair upsert failed due to constraint violation") from e
    except OperationalError as e:
        logger.error(f"Database connection error in upsert_confusion_pair: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error upserting confusion pair for user {user_id}: {e}")
        raise DatabaseError(f"Failed to upsert confusion pair: {e}") from e
