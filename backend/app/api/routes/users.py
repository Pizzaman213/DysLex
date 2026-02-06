"""User management endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserId, DbSession
from app.models.user import User, UserCreate, UserUpdate

router = APIRouter()


@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: DbSession,
) -> User:
    """Create a new user."""
    # Placeholder - would create in database
    return User(
        id="new-user-id",
        email=user_data.email,
        name=user_data.name,
    )


@router.get("/me", response_model=User)
async def get_current_user(
    user_id: CurrentUserId,
    db: DbSession,
) -> User:
    """Get the current user's profile."""
    # Placeholder - would query from database
    return User(
        id=user_id,
        email="demo@example.com",
        name="Demo User",
    )


@router.patch("/me", response_model=User)
async def update_current_user(
    update: UserUpdate,
    user_id: CurrentUserId,
    db: DbSession,
) -> User:
    """Update the current user's profile."""
    return User(
        id=user_id,
        email=update.email or "demo@example.com",
        name=update.name or "Demo User",
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    user_id: CurrentUserId,
    db: DbSession,
) -> None:
    """Delete the current user's account."""
    pass
