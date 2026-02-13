"""Folder repository."""

import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import Folder

logger = logging.getLogger(__name__)


async def get_folders_by_user(db: AsyncSession, user_id: str) -> list[Folder]:
    """Get all folders for a user ordered by sort_order."""
    try:
        result = await db.execute(
            select(Folder)
            .where(Folder.user_id == user_id)
            .order_by(Folder.sort_order)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_folders_by_user for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting folders for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get folders: {e}") from e


async def get_folder_by_id(db: AsyncSession, folder_id: str, user_id: str) -> Folder | None:
    """Get a single folder by ID scoped to a user."""
    try:
        result = await db.execute(
            select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_folder_by_id: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting folder {folder_id}: {e}")
        raise DatabaseError(f"Failed to get folder: {e}") from e


async def create_folder(db: AsyncSession, user_id: str, folder_id: str, name: str, sort_order: int = 0) -> Folder:
    """Create a new folder."""
    try:
        folder = Folder(
            id=folder_id,
            user_id=user_id,
            name=name,
            sort_order=sort_order,
        )
        db.add(folder)
        await db.flush()
        await db.refresh(folder)
        return folder
    except IntegrityError as e:
        logger.error(f"Duplicate folder {folder_id} for user {user_id}: {e}")
        raise DuplicateRecordError(f"Folder {folder_id} already exists") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_folder: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating folder: {e}")
        raise DatabaseError(f"Failed to create folder: {e}") from e


async def update_folder(db: AsyncSession, folder_id: str, user_id: str, updates: dict[str, object]) -> Folder | None:
    """Update a folder. Returns None if not found."""
    try:
        folder = await get_folder_by_id(db, folder_id, user_id)
        if not folder:
            return None
        for key, value in updates.items():
            if hasattr(folder, key):
                setattr(folder, key, value)
        await db.flush()
        await db.refresh(folder)
        return folder
    except OperationalError as e:
        logger.error(f"Database connection error in update_folder: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error updating folder {folder_id}: {e}")
        raise DatabaseError(f"Failed to update folder: {e}") from e


async def delete_folder(db: AsyncSession, folder_id: str, user_id: str) -> bool:
    """Delete a folder. Returns True if deleted."""
    try:
        result = await db.execute(
            delete(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        await db.flush()
        return bool(result.rowcount > 0)  # type: ignore[union-attr]
    except OperationalError as e:
        logger.error(f"Database connection error in delete_folder: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error deleting folder {folder_id}: {e}")
        raise DatabaseError(f"Failed to delete folder: {e}") from e


async def bulk_upsert_folders(db: AsyncSession, user_id: str, folders: list[dict[str, Any]]) -> int:
    """Upsert a list of folders for a user. Returns count of rows affected."""
    try:
        count = 0
        for f in folders:
            existing = await get_folder_by_id(db, f["id"], user_id)
            if existing:
                for key, value in f.items():
                    if key != "id" and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                folder = Folder(
                    id=f["id"],
                    user_id=user_id,
                    name=f.get("name", "New Folder"),
                    sort_order=f.get("sort_order", 0),
                )
                db.add(folder)
            count += 1
        await db.flush()
        return count
    except OperationalError as e:
        logger.error(f"Database connection error in bulk_upsert_folders: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in bulk_upsert_folders for user {user_id}: {e}")
        raise DatabaseError(f"Failed to bulk upsert folders: {e}") from e
