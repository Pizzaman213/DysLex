"""Tests for error profile functionality."""

import pytest

from app.core.error_profile import get_user_profile


@pytest.mark.asyncio
async def test_get_user_profile():
    """Test getting user error profile."""
    # Placeholder test - would use test database
    profile = await get_user_profile("test-user", None)
    assert profile.user_id == "test-user"
    assert profile.overall_score >= 0
    assert isinstance(profile.top_patterns, list)
