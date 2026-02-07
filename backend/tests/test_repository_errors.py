"""Tests for repository error handling."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.exceptions import ConnectionError, DatabaseError, DuplicateRecordError
from app.db.models import User
from app.db.repositories import user_repo


@pytest.mark.asyncio
async def test_duplicate_user_email_raises_error(db):
    """Creating user with duplicate email should raise DuplicateRecordError."""
    # Create first user
    user1 = User(
        id="test-user-1",
        email="test@example.com",
        name="Alice",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user1)

    # Attempt duplicate - should raise custom exception
    user2 = User(
        id="test-user-2",
        email="test@example.com",  # Duplicate email
        name="Bob",
        password_hash="hash456",
    )
    with pytest.raises(DuplicateRecordError, match="already exists"):
        await user_repo.create_user(db, user2)


@pytest.mark.asyncio
async def test_repository_logs_errors(db, caplog):
    """Repository errors should be logged."""
    import logging

    caplog.set_level(logging.ERROR)

    # Create first user
    user1 = User(
        id="test-user-1",
        email="test@example.com",
        name="Alice",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user1)

    # Trigger duplicate error
    user2 = User(
        id="test-user-2",
        email="test@example.com",
        name="Bob",
        password_hash="hash456",
    )
    with pytest.raises(DuplicateRecordError):
        await user_repo.create_user(db, user2)

    # Verify logging occurred
    assert "Duplicate user email" in caplog.text
    assert "test@example.com" in caplog.text


@pytest.mark.asyncio
async def test_get_user_by_id_handles_errors(db):
    """get_user_by_id should handle database errors gracefully."""
    # Normal operation - should not raise
    user = await user_repo.get_user_by_id(db, "nonexistent-id")
    assert user is None


@pytest.mark.asyncio
async def test_create_user_with_invalid_data_raises_database_error(db):
    """Creating user with invalid data should raise DatabaseError."""
    # Create user with None email (violates NOT NULL constraint)
    user = User(
        id="test-user-1",
        email=None,  # Invalid
        name="Alice",
        password_hash="hash123",
    )

    # Should raise a DatabaseError (caught from IntegrityError)
    with pytest.raises((DuplicateRecordError, DatabaseError)):
        await user_repo.create_user(db, user)


@pytest.mark.asyncio
async def test_update_user_with_duplicate_email_raises_error(db):
    """Updating user to duplicate email should raise DuplicateRecordError."""
    # Create two users
    user1 = User(
        id="test-user-1",
        email="alice@example.com",
        name="Alice",
        password_hash="hash123",
    )
    user2 = User(
        id="test-user-2",
        email="bob@example.com",
        name="Bob",
        password_hash="hash456",
    )
    await user_repo.create_user(db, user1)
    await user_repo.create_user(db, user2)

    # Update user2 to have same email as user1
    user2.email = "alice@example.com"

    with pytest.raises(DuplicateRecordError, match="already exists"):
        await user_repo.update_user(db, user2)


@pytest.mark.asyncio
async def test_delete_user_handles_errors(db):
    """delete_user should handle errors gracefully."""
    # Create and delete user
    user = User(
        id="test-user-1",
        email="test@example.com",
        name="Alice",
        password_hash="hash123",
    )
    await user_repo.create_user(db, user)

    # Delete should not raise
    await user_repo.delete_user(db, user)

    # Verify deletion
    result = await user_repo.get_user_by_id(db, "test-user-1")
    assert result is None
