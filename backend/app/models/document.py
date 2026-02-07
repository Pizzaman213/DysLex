"""Document and folder Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Folder schemas
# ---------------------------------------------------------------------------

class FolderCreate(BaseModel):
    """Create a folder."""

    id: str
    name: str = "New Folder"
    sort_order: int = 0


class FolderUpdate(BaseModel):
    """Partial update for a folder."""

    name: str | None = None
    sort_order: int | None = None


class FolderResponse(BaseModel):
    """Folder returned to the client."""

    id: str
    name: str
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Document schemas
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    """Create a document."""

    id: str
    title: str = "Untitled Document"
    content: str = ""
    mode: str = "draft"
    folder_id: str | None = None
    sort_order: int = 0


class DocumentUpdate(BaseModel):
    """Partial update for a document."""

    title: str | None = None
    content: str | None = None
    mode: str | None = None
    folder_id: str | None = None
    sort_order: int | None = None


class DocumentResponse(BaseModel):
    """Document returned to the client."""

    id: str
    title: str
    content: str
    mode: str
    folder_id: str | None = None
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Bulk sync
# ---------------------------------------------------------------------------

class BulkSyncDocument(BaseModel):
    """A single document inside a bulk sync payload."""

    id: str
    title: str = "Untitled Document"
    content: str = ""
    mode: str = "draft"
    folder_id: str | None = None
    sort_order: int = 0


class BulkSyncFolder(BaseModel):
    """A single folder inside a bulk sync payload."""

    id: str
    name: str = "New Folder"
    sort_order: int = 0


class BulkSyncRequest(BaseModel):
    """Full-state upload from localStorage to the server."""

    documents: list[BulkSyncDocument] = []
    folders: list[BulkSyncFolder] = []
