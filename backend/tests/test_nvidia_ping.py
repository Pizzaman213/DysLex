"""Test that NVIDIA NIM servers are reachable.

These tests make real HTTP requests to the NVIDIA NIM API endpoints
to verify connectivity. They require a valid NVIDIA_NIM_API_KEY
environment variable and network access, so they are marked with
``pytest.mark.nvidia`` for easy filtering.

Run with:
    pytest tests/test_nvidia_ping.py -v
Skip in CI:
    pytest -m "not nvidia"
"""

import pytest
import httpx

from app.config import settings

# All tests in this module need a real API key and network access.
pytestmark = [
    pytest.mark.nvidia,
    pytest.mark.asyncio,
]

NIM_LLM_URL = f"{settings.nvidia_nim_llm_url}/chat/completions"
NIM_VOICE_URL = settings.nvidia_nim_voice_url
TIMEOUT = httpx.Timeout(15.0, connect=10.0)


def _skip_if_no_api_key():
    if not settings.nvidia_nim_api_key:
        pytest.skip("NVIDIA_NIM_API_KEY not set — skipping live ping")


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.nvidia_nim_api_key}",
        "Content-Type": "application/json",
    }


class TestNvidiaLLMPing:
    """Verify the NVIDIA NIM LLM endpoint is reachable and responds."""

    async def test_llm_endpoint_responds(self):
        """Send a minimal chat completion request and confirm a 200 response."""
        _skip_if_no_api_key()

        payload = {
            "model": settings.nvidia_nim_llm_model,
            "messages": [{"role": "user", "content": "Say hello."}],
            "max_tokens": 8,
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                NIM_LLM_URL,
                headers=_auth_headers(),
                json=payload,
            )

        assert response.status_code == 200, (
            f"NIM LLM returned {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "choices" in body, f"Unexpected response shape: {body}"

    async def test_llm_invalid_key_returns_401(self):
        """Confirm the endpoint rejects an invalid API key."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                NIM_LLM_URL,
                headers={
                    "Authorization": "Bearer invalid-key-000",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia_nim_llm_model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )

        assert response.status_code in (401, 403), (
            f"Expected 401/403 for bad key, got {response.status_code}"
        )


class TestNvidiaVisionPing:
    """Verify the NVIDIA NIM vision model endpoint is reachable."""

    async def test_vision_endpoint_responds(self):
        """Send a minimal request to the vision model and confirm 200."""
        _skip_if_no_api_key()

        payload = {
            "model": settings.nvidia_nim_vision_model,
            "messages": [{"role": "user", "content": "Describe what you see."}],
            "max_tokens": 8,
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{settings.nvidia_nim_llm_url}/chat/completions",
                headers=_auth_headers(),
                json=payload,
            )

        # Vision model may return 200 or 400 (no image provided) — both prove
        # the server is reachable and processing requests.
        assert response.status_code in (200, 400), (
            f"NIM Vision returned {response.status_code}: {response.text}"
        )


class TestNvidiaModelsEndpoint:
    """Verify the /models listing endpoint works."""

    async def test_list_models(self):
        """GET /models should return available models."""
        _skip_if_no_api_key()

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{settings.nvidia_nim_llm_url}/models",
                headers=_auth_headers(),
            )

        assert response.status_code == 200, (
            f"NIM /models returned {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "data" in body, f"Unexpected /models response: {body}"
