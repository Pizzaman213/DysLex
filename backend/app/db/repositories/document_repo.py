"""Document repository."""

import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import Document

logger = logging.getLogger(__name__)


async def get_documents_by_user(db: AsyncSession, user_id: str) -> list[Document]:
    """Get all documents for a user ordered by sort_order."""
    try:
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.sort_order)
        )
        return list(result.scalars().all())
    except OperationalError as e:
        logger.error(f"Database connection error in get_documents_by_user for user {user_id}: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting documents for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get documents: {e}") from e


async def get_document_by_id(db: AsyncSession, doc_id: str, user_id: str) -> Document | None:
    """Get a single document by ID scoped to a user."""
    try:
        result = await db.execute(
            select(Document).where(Document.id == doc_id, Document.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error in get_document_by_id: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error getting document {doc_id}: {e}")
        raise DatabaseError(f"Failed to get document: {e}") from e


async def create_document(
    db: AsyncSession,
    user_id: str,
    doc_id: str,
    title: str = "Untitled Document",
    content: str = "",
    mode: str = "draft",
    folder_id: str | None = None,
    sort_order: int = 0,
) -> Document:
    """Create a new document."""
    try:
        doc = Document(
            id=doc_id,
            user_id=user_id,
            title=title,
            content=content,
            mode=mode,
            folder_id=folder_id,
            sort_order=sort_order,
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)
        return doc
    except IntegrityError as e:
        logger.error(f"Duplicate document {doc_id} for user {user_id}: {e}")
        raise DuplicateRecordError(f"Document {doc_id} already exists") from e
    except OperationalError as e:
        logger.error(f"Database connection error in create_document: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error creating document: {e}")
        raise DatabaseError(f"Failed to create document: {e}") from e


async def update_document(db: AsyncSession, doc_id: str, user_id: str, updates: dict[str, object]) -> Document | None:
    """Update a document. Returns None if not found."""
    try:
        doc = await get_document_by_id(db, doc_id, user_id)
        if not doc:
            return None
        for key, value in updates.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        await db.flush()
        await db.refresh(doc)
        return doc
    except OperationalError as e:
        logger.error(f"Database connection error in update_document: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error updating document {doc_id}: {e}")
        raise DatabaseError(f"Failed to update document: {e}") from e


async def delete_document(db: AsyncSession, doc_id: str, user_id: str) -> bool:
    """Delete a document. Returns True if deleted."""
    try:
        result = await db.execute(
            delete(Document).where(Document.id == doc_id, Document.user_id == user_id)
        )
        await db.flush()
        return bool(result.rowcount > 0)  # type: ignore[union-attr]
    except OperationalError as e:
        logger.error(f"Database connection error in delete_document: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error deleting document {doc_id}: {e}")
        raise DatabaseError(f"Failed to delete document: {e}") from e


async def bulk_upsert_documents(db: AsyncSession, user_id: str, documents: list[dict[str, Any]]) -> int:
    """Upsert a list of documents for a user. Returns count of rows affected."""
    try:
        count = 0
        for d in documents:
            existing = await get_document_by_id(db, d["id"], user_id)
            if existing:
                for key, value in d.items():
                    if key != "id" and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                doc = Document(
                    id=d["id"],
                    user_id=user_id,
                    title=d.get("title", "Untitled Document"),
                    content=d.get("content", ""),
                    mode=d.get("mode", "draft"),
                    folder_id=d.get("folder_id"),
                    sort_order=d.get("sort_order", 0),
                )
                db.add(doc)
            count += 1
        await db.flush()
        return count
    except OperationalError as e:
        logger.error(f"Database connection error in bulk_upsert_documents: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in bulk_upsert_documents for user {user_id}: {e}")
        raise DatabaseError(f"Failed to bulk upsert documents: {e}") from e
