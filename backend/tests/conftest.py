"""Shared test fixtures for DysLex AI backend tests."""

import math
import struct
import uuid
import wave

import pytest
import pytest_asyncio
from sqlalchemy import JSON, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, User


# Use an in-memory SQLite database for tests.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# SQLite doesn't support JSONB — remap to plain JSON at the dialect level.
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    # Register date_trunc for SQLite (PostgreSQL built-in, not available in SQLite)
    def _date_trunc(part, value):
        if value is None:
            return None
        from datetime import datetime as _dt

        try:
            dt = _dt.fromisoformat(value)
        except (TypeError, ValueError):
            return value
        if part == "week":
            dt = dt - __import__("datetime").timedelta(days=dt.weekday())
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if part == "month":
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        if part == "day":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return value

    dbapi_connection.create_function("date_trunc", 2, _date_trunc)


# Monkey-patch JSONB columns to render as JSON for SQLite tests.
from sqlalchemy.dialects.postgresql import JSONB as _JSONB  # noqa: E402

_original_compile = None


def _register_jsonb_for_sqlite():
    """Register a compilation rule so JSONB compiles to JSON on SQLite."""
    from sqlalchemy.ext.compiler import compiles

    @compiles(_JSONB, "sqlite")
    def _compile_jsonb_sqlite(element, compiler, **kw):
        return "JSON"


_register_jsonb_for_sqlite()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """Create tables and yield a fresh async session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db: AsyncSession) -> AsyncSession:
    """Alias for the ``db`` fixture used by some test modules."""
    return db


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Create and return a test user."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        password_hash="fakehash",
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
def wav_fixture(tmp_path):
    """Generate a minimal valid WAV file (100ms of 440Hz sine, 16kHz mono)."""
    filepath = tmp_path / "test_audio_short.wav"
    sample_rate = 16000
    duration = 0.1  # 100ms
    n_samples = int(sample_rate * duration)

    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            sample = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            wf.writeframes(struct.pack("<h", sample))

    return filepath


@pytest.fixture
def webm_fixture(tmp_path):
    """Create a minimal file with WebM magic bytes (EBML header)."""
    filepath = tmp_path / "test_audio.webm"
    # WebM files start with the EBML magic bytes: 0x1A45DFA3
    webm_header = b"\x1a\x45\xdf\xa3" + b"\x00" * 96
    filepath.write_bytes(webm_header)
    return filepath
