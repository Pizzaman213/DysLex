"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import corrections, profiles, progress, users, voice
from app.config import settings

app = FastAPI(
    title="DysLex AI API",
    description="Intelligent writing assistance for dyslexic users",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(corrections.router, prefix="/api/corrections", tags=["corrections"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "DysLex AI API", "docs": "/docs"}
