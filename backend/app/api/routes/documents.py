"""Document and folder CRUD + bulk sync endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserId, DbSession
from app.db.repositories import document_repo, folder_repo
from app.models.document import (
    BulkSyncRequest,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    FolderCreate,
    FolderResponse,
    FolderUpdate,
)
from app.models.envelope import success_response

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# List all documents + folders
# ---------------------------------------------------------------------------

@router.get("")
async def list_documents(
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Return all documents and folders for the current user."""
    documents = await document_repo.get_documents_by_user(db, current_user)
    folders = await folder_repo.get_folders_by_user(db, current_user)
    return success_response({
        "documents": [DocumentResponse.model_validate(d).model_dump() for d in documents],
        "folders": [FolderResponse.model_validate(f).model_dump() for f in folders],
    })


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------

@router.post("/docs", status_code=status.HTTP_201_CREATED)
async def create_document(
    body: DocumentCreate,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Create a new document."""
    doc = await document_repo.create_document(
        db,
        user_id=current_user,
        doc_id=body.id,
        title=body.title,
        content=body.content,
        mode=body.mode,
        folder_id=body.folder_id,
        sort_order=body.sort_order,
    )
    return success_response(DocumentResponse.model_validate(doc).model_dump())


@router.patch("/docs/{doc_id}")
async def update_document(
    doc_id: str,
    body: DocumentUpdate,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Partial update of a document."""
    updates = body.model_dump(exclude_unset=True)
    doc = await document_repo.update_document(db, doc_id, current_user, updates)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return success_response(DocumentResponse.model_validate(doc).model_dump())


@router.delete("/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> None:
    """Delete a document."""
    deleted = await document_repo.delete_document(db, doc_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


# ---------------------------------------------------------------------------
# Folder CRUD
# ---------------------------------------------------------------------------

@router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderCreate,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Create a new folder."""
    folder = await folder_repo.create_folder(
        db,
        user_id=current_user,
        folder_id=body.id,
        name=body.name,
        sort_order=body.sort_order,
    )
    return success_response(FolderResponse.model_validate(folder).model_dump())


@router.patch("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    body: FolderUpdate,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Partial update of a folder."""
    updates = body.model_dump(exclude_unset=True)
    folder = await folder_repo.update_folder(db, folder_id, current_user, updates)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return success_response(FolderResponse.model_validate(folder).model_dump())


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder_endpoint(
    folder_id: str,
    current_user: CurrentUserId,
    db: DbSession,
) -> None:
    """Delete a folder. Documents inside move to root (SET NULL)."""
    deleted = await folder_repo.delete_folder(db, folder_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")


# ---------------------------------------------------------------------------
# Bulk sync (initial localStorage → DB migration)
# ---------------------------------------------------------------------------

@router.put("/sync")
async def sync_documents(
    body: BulkSyncRequest,
    current_user: CurrentUserId,
    db: DbSession,
) -> dict:
    """Bulk upsert all documents and folders.

    Used when the frontend detects that the server has no data and
    needs to push the full localStorage state up.
    """
    folder_count = await folder_repo.bulk_upsert_folders(
        db, current_user, [f.model_dump() for f in body.folders]
    )
    doc_count = await document_repo.bulk_upsert_documents(
        db, current_user, [d.model_dump() for d in body.documents]
    )
    return success_response({
        "folders_synced": folder_count,
        "documents_synced": doc_count,
    })
