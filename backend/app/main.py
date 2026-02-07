"""FastAPI application entry point."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import (
    auth,
    capture,
    corrections,
    learn,
    log_correction,
    profiles,
    progress,
    scaffold,
    snapshots,
    users,
    voice,
)
from app.config import settings
from app.middleware.rate_limiter import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.services.redis_client import close_redis, get_redis
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.tts_service import cleanup_old_audio_files

logger = logging.getLogger(__name__)

# Configure logging format based on dev_mode
if not settings.dev_mode:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
    )
else:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


async def periodic_cleanup():
    """Run TTS cleanup task every hour."""
    while True:
        await asyncio.to_thread(cleanup_old_audio_files)
        await asyncio.sleep(3600)


_cleanup_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    global _cleanup_task
    # Startup
    await get_redis()  # Initialize Redis connection pool
    start_scheduler()  # Start background job scheduler
    _cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    # Shutdown
    if _cleanup_task is not None:
        _cleanup_task.cancel()
        _cleanup_task = None
    stop_scheduler()  # Stop background jobs
    await close_redis()  # Close Redis connection pool

app = FastAPI(
    title="DysLex AI API",
    description="Intelligent writing assistance for dyslexic users",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs" if settings.dev_mode else None,
    redoc_url="/redoc" if settings.dev_mode else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------------------

# Create audio storage directory on startup
os.makedirs(settings.tts_audio_dir, exist_ok=True)

# Mount static files for audio serving
app.mount("/audio", StaticFiles(directory=settings.tts_audio_dir), name="audio")

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.state.limiter = limiter


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if not settings.dev_mode:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "data": None,
            "errors": [{"code": "RATE_LIMITED", "message": str(exc.detail), "field": None}],
            "meta": {},
        },
    )


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=True)
    detail = str(exc) if settings.dev_mode else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "errors": [{"code": "INTERNAL_ERROR", "message": detail, "field": None}],
            "meta": {},
        },
    )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ---------------------------------------------------------------------------
# Routers — all under /api/v1/
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(corrections.router, prefix="/api/v1/correct", tags=["corrections"])
app.include_router(profiles.router, prefix="/api/v1/profile", tags=["profiles"])
app.include_router(snapshots.router, prefix="/api/v1", tags=["adaptive-learning"])
app.include_router(learn.router, prefix="/api/v1/learn", tags=["adaptive-learning"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(capture.router, prefix="/api/v1/capture", tags=["capture"])
app.include_router(
    log_correction.router, prefix="/api/v1/log-correction", tags=["passive-learning"],
)
app.include_router(progress.router, prefix="/api/v1/progress", tags=["progress"])
app.include_router(scaffold.router, prefix="/api/v1/scaffold", tags=["scaffold"])

# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> dict:
    """Liveness check — verifies the API process is alive."""
    return {
        "status": "healthy",
        "services": {
            "database": "ok",
            "nim_api": "ok" if settings.nvidia_nim_api_key else "not_configured",
        },
    }


@app.get("/health/ready")
async def readiness_check() -> JSONResponse:
    """Readiness check — verifies DB and Redis are reachable."""
    checks: dict[str, str] = {}

    # Check database
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # Check Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "services": checks},
    )


@app.get("/api/v1/version")
async def version() -> dict:
    """Return build / version metadata."""
    return {
        "version": app.version,
        "title": app.title,
        "api_prefix": "/api/v1",
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "DysLex AI API", "docs": "/docs"}
