"""Tests for correction endpoints and API gateway fundamentals."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Override the DB dependency so we never hit a real database
# ---------------------------------------------------------------------------


async def _fake_db():
    """Yield a mocked AsyncSession — endpoints won't touch the DB."""
    yield AsyncMock(spec=AsyncSession)


app.dependency_overrides[get_db] = _fake_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health / system
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint should return 200 and status healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_version_endpoint(client: AsyncClient):
    """Version endpoint should return version metadata."""
    response = await client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert "version" in body


# ---------------------------------------------------------------------------
# Corrections — unauthenticated (uses demo-user-id fallback)
# ---------------------------------------------------------------------------


_FAKE_PROFILE = AsyncMock()
_FAKE_PROFILE.top_patterns = []
_FAKE_PROFILE.confusion_pairs = []
_FAKE_PROFILE.overall_score = 50


@pytest.mark.asyncio
@patch("app.core.llm_orchestrator.get_user_profile", return_value=_FAKE_PROFILE)
async def test_auto_correction_returns_envelope(_mock, client: AsyncClient):
    """POST /api/v1/correct/auto should return a response envelope."""
    response = await client.post(
        "/api/v1/correct/auto",
        json={"text": "Teh quick brown fox"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "data" in body
    assert "corrections" in body["data"]
    assert "meta" in body
    assert "request_id" in body["meta"]
    assert "processing_time_ms" in body["meta"]
    assert "tier_used" in body["meta"]


@pytest.mark.asyncio
@patch("app.core.llm_orchestrator.get_user_profile", return_value=_FAKE_PROFILE)
async def test_quick_correction_endpoint(_mock, client: AsyncClient):
    """POST /api/v1/correct/quick should succeed."""
    response = await client.post(
        "/api/v1/correct/quick",
        json={"text": "speling eror"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"


@pytest.mark.asyncio
@patch("app.core.llm_orchestrator.get_user_profile", return_value=_FAKE_PROFILE)
async def test_deep_correction_endpoint(_mock, client: AsyncClient):
    """POST /api/v1/correct/deep should succeed."""
    response = await client.post(
        "/api/v1/correct/deep",
        json={"text": "Their going to the store over they're."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"


@pytest.mark.asyncio
@patch("app.core.llm_orchestrator.get_user_profile", return_value=_FAKE_PROFILE)
async def test_document_correction_endpoint(_mock, client: AsyncClient):
    """POST /api/v1/correct/document should succeed."""
    response = await client.post(
        "/api/v1/correct/document",
        json={"text": "A longer document with multiple paragraphs."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"


# ---------------------------------------------------------------------------
# Auth — token validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoint_with_invalid_token(client: AsyncClient):
    """Sending a malformed JWT should return 401."""
    response = await client.post(
        "/api/v1/correct/auto",
        json={"text": "hello"},
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# OpenAPI docs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_docs_available(client: AsyncClient):
    """OpenAPI JSON spec should be served at /api/v1/openapi.json."""
    response = await client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert "paths" in body
