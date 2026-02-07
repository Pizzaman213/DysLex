"""Per-user rate limiting using slowapi."""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


def _get_user_or_ip(request: Request) -> str:
    """Extract user ID from JWT for rate-limit key, fall back to IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.api.dependencies import verify_token
            payload = verify_token(auth.split(" ", 1)[1])
            return payload["sub"]
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip)

# Convenience limit strings built from config
LLM_LIMIT = f"{settings.rate_limit_llm}/minute"
VOICE_LIMIT = f"{settings.rate_limit_voice}/minute"
DEFAULT_LIMIT = "60/minute"


def rate_limit_exceeded_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a JSON envelope when rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "data": None,
            "errors": [{"code": "RATE_LIMITED", "message": str(exc.detail), "field": None}],
            "meta": {},
        },
    )
