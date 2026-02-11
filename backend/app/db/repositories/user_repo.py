"""User repository."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import User

logger = logging.getLogger(__name__)


async def get_all_user_ids(db: AsyncSession) -> list[str]:
    """Return all user IDs (lightweight — no full ORM objects loaded)."""
    try:
        result = await db.execute(select(User.id))
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_all_user_ids: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in get_all_user_ids: {e}")
        raise DatabaseError(f"Failed to get user IDs: {e}") from e


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get a user by ID."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_user_by_id for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting user {user_id}: {e}")
        raise DatabaseError(f"Failed to get user: {e}") from e


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email."""
    try:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_user_by_email for {email}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting user by email {email}: {e}")
        raise DatabaseError(f"Failed to get user: {e}") from e


async def create_user(db: AsyncSession, user: User) -> User:
    """Create a new user."""
    try:
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user
    except IntegrityError as e:
        logger.error(f"Duplicate user email {user.email}: {e}")
        raise DuplicateRecordError(f"User with email {user.email} already exists") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_user: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating user: {e}")
        raise DatabaseError(f"Failed to create user: {e}") from e


async def update_user(db: AsyncSession, user: User) -> User:
    """Update a user."""
    try:
        await db.flush()
        await db.refresh(user)
        return user
    except IntegrityError as e:
        logger.error(f"Integrity error updating user {user.id}: {e}")
        raise DuplicateRecordError(f"User with email {user.email} already exists") from e
    except OperationalError as e:
        logger.error(f"Database connection error in update_user: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error updating user {user.id}: {e}")
        raise DatabaseError(f"Failed to update user: {e}") from e


async def delete_user(db: AsyncSession, user: User) -> None:
    """Delete a user."""
    try:
        await db.delete(user)
    except OperationalError as e:
        logger.error(f"Database connection error in delete_user for user {user.id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error deleting user {user.id}: {e}")
        raise DatabaseError(f"Failed to delete user: {e}") from e
