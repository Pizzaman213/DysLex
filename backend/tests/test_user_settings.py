"""Tests for user settings endpoints and repository."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User as UserORM, UserSettings as UserSettingsORM
from app.db.repositories.settings_repo import (
    create_default_settings,
    get_or_create_settings,
    get_settings_by_user_id,
    update_settings,
)


async def _create_test_user(db: AsyncSession) -> str:
    """Create a test user and return its ID."""
    user_id = str(uuid.uuid4())
    user = UserORM(id=user_id, email=f"{user_id}@test.com", name="Test", password_hash="x")
    db.add(user)
    await db.flush()
    return user_id


@pytest.mark.asyncio
async def test_create_default_settings(db_session: AsyncSession):
    """Test creating default settings for a user."""
    user_id = await _create_test_user(db_session)

    settings = await create_default_settings(db_session, user_id)

    assert settings.user_id == user_id
    assert settings.language == "en"
    assert settings.theme == "cream"
    assert settings.font == "OpenDyslexic"
    assert settings.font_size == 18
    assert settings.voice_enabled is True
    assert settings.auto_correct is True
    assert settings.cloud_sync is False
    assert settings.developer_mode is False


@pytest.mark.asyncio
async def test_get_settings_by_user_id(db_session: AsyncSession):
    """Test retrieving settings by user ID."""
    user_id = await _create_test_user(db_session)

    # Create settings first
    created = await create_default_settings(db_session, user_id)

    # Retrieve settings
    settings = await get_settings_by_user_id(db_session, user_id)

    assert settings is not None
    assert settings.id == created.id
    assert settings.user_id == user_id


@pytest.mark.asyncio
async def test_get_settings_nonexistent_user(db_session: AsyncSession):
    """Test retrieving settings for a user that doesn't exist."""
    settings = await get_settings_by_user_id(db_session, str(uuid.uuid4()))
    assert settings is None


@pytest.mark.asyncio
async def test_update_settings(db_session: AsyncSession):
    """Test updating user settings."""
    user_id = await _create_test_user(db_session)

    # Create default settings
    await create_default_settings(db_session, user_id)

    # Update settings
    updates = {
        "theme": "night",
        "font_size": 20,
        "developer_mode": True,
    }
    updated = await update_settings(db_session, user_id, updates)

    assert updated is not None
    assert updated.theme == "night"
    assert updated.font_size == 20
    assert updated.developer_mode is True
    # Ensure other fields remain unchanged
    assert updated.language == "en"
    assert updated.font == "OpenDyslexic"


@pytest.mark.asyncio
async def test_get_or_create_settings_creates_if_missing(db_session: AsyncSession):
    """Test get_or_create creates settings if they don't exist."""
    user_id = await _create_test_user(db_session)

    settings = await get_or_create_settings(db_session, user_id)

    assert settings is not None
    assert settings.user_id == user_id
    assert settings.language == "en"


@pytest.mark.asyncio
async def test_get_or_create_settings_returns_existing(db_session: AsyncSession):
    """Test get_or_create returns existing settings."""
    user_id = await _create_test_user(db_session)

    # Create settings with custom values
    created = await create_default_settings(db_session, user_id)
    await update_settings(db_session, user_id, {"theme": "night"})

    # Get or create should return existing
    settings = await get_or_create_settings(db_session, user_id)

    assert settings is not None
    assert settings.id == created.id
    assert settings.theme == "night"


# API endpoint tests would go here
# These would require the FastAPI test client and proper auth setup
# Example:
#
# @pytest.mark.asyncio
# async def test_get_settings_endpoint(client: AsyncClient):
#     """Test GET /api/v1/users/{user_id}/settings endpoint."""
#     response = await client.get("/api/v1/users/demo-user-id/settings")
#     assert response.status_code == 200
#     assert response.json()["status"] == "success"
#     assert "data" in response.json()
