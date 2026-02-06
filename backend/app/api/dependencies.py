"""API dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_id() -> str:
    """Get current authenticated user ID. Placeholder for auth implementation."""
    # TODO: Implement proper JWT authentication
    return "demo-user-id"


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
