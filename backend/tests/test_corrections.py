"""Tests for correction endpoints."""

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_create_corrections(client: AsyncClient):
    """Test correction creation endpoint."""
    response = await client.post(
        "/api/corrections",
        json={"text": "Teh quick brown fox"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "corrections" in data
