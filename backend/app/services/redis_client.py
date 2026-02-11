"""Redis client for snapshot storage.

Provides ephemeral storage for text snapshots with automatic TTL.
Snapshots are privacy-first: stored for 24 hours max, then auto-deleted.
"""

import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.core.adaptive_loop import TextSnapshot

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance (creates connection pool on first call)."""
    global _redis_pool, _redis_client

    if _redis_client is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=10,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        logger.info("Redis connection pool initialized")

    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool, _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None

    logger.info("Redis connection pool closed")


# ---------------------------------------------------------------------------
# Generic cache helpers — fail silently so Redis outages never break the app
# ---------------------------------------------------------------------------


async def cache_get(key: str) -> Any | None:
    """Get a cached value by key. Returns None on miss or error."""
    try:
        client = await get_redis()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.debug("Cache miss/error for key %s", key, exc_info=True)
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 600) -> None:
    """Store a value in cache with TTL. Fails silently."""
    try:
        client = await get_redis()
        await client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.debug("Cache set failed for key %s", key, exc_info=True)


async def cache_delete(key: str) -> None:
    """Delete a cached key. Fails silently."""
    try:
        client = await get_redis()
        await client.delete(key)
    except Exception:
        logger.debug("Cache delete failed for key %s", key, exc_info=True)


class SnapshotStore:
    """Redis-backed snapshot storage with automatic TTL."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl_seconds = settings.snapshot_ttl_hours * 3600

    def _snapshot_key(self, user_id: str, index: int) -> str:
        """Generate Redis key for snapshot."""
        return f"snapshot:{user_id}:{index}"

    def _snapshot_list_key(self, user_id: str) -> str:
        """Generate Redis key for user's snapshot list (stores indices)."""
        return f"snapshots:{user_id}"

    async def store_snapshot(self, user_id: str, snapshot: TextSnapshot) -> None:
        """Store a snapshot with automatic TTL.

        Maintains a rolling window of recent snapshots per user.
        Automatically expires after configured TTL for privacy.
        """
        # Get current snapshot count
        list_key = self._snapshot_list_key(user_id)
        count = await self.redis.llen(list_key)  # type: ignore[misc]

        # Store snapshot data
        snapshot_data = {
            "text": snapshot.text,
            "timestamp": snapshot.timestamp.isoformat(),
            "word_count": snapshot.word_count,
        }

        snapshot_key = self._snapshot_key(user_id, count)
        await self.redis.setex(  # type: ignore[misc]
            snapshot_key,
            self.ttl_seconds,
            json.dumps(snapshot_data),
        )

        # Add to user's snapshot list
        await self.redis.rpush(list_key, str(count))  # type: ignore[misc]
        await self.redis.expire(list_key, self.ttl_seconds)  # type: ignore[misc]

        # Limit to last 50 snapshots (memory bounded)
        if count >= 50:
            # Remove oldest snapshot reference
            oldest_idx = await self.redis.lpop(list_key)  # type: ignore[misc]
            if oldest_idx:
                oldest_key = self._snapshot_key(user_id, int(str(oldest_idx)))
                await self.redis.delete(oldest_key)  # type: ignore[misc]

        logger.debug(
            "Stored snapshot for user %s (index %d, %d words)",
            user_id, count, snapshot.word_count
        )

    async def get_last_snapshot(self, user_id: str) -> TextSnapshot | None:
        """Retrieve the most recent snapshot for a user."""
        list_key = self._snapshot_list_key(user_id)
        count = await self.redis.llen(list_key)  # type: ignore[misc]

        if count == 0:
            return None

        # Get last index
        indices = await self.redis.lrange(list_key, -1, -1)  # type: ignore[misc]
        if not indices:
            return None

        last_index = int(indices[0])
        snapshot_key = self._snapshot_key(user_id, last_index)

        data = await self.redis.get(snapshot_key)  # type: ignore[misc]
        if not data:
            return None

        snapshot_dict = json.loads(data)
        return TextSnapshot(
            text=snapshot_dict["text"],
            timestamp=datetime.fromisoformat(snapshot_dict["timestamp"]),
            word_count=snapshot_dict["word_count"],
        )

    async def get_recent_snapshots(
        self, user_id: str, limit: int = 10
    ) -> list[TextSnapshot]:
        """Retrieve recent snapshots for a user (for debugging/analysis)."""
        list_key = self._snapshot_list_key(user_id)
        count = await self.redis.llen(list_key)  # type: ignore[misc]

        if count == 0:
            return []

        # Get last N indices
        start = max(0, count - limit)
        indices = await self.redis.lrange(list_key, start, -1)  # type: ignore[misc]

        snapshots = []
        for idx_str in indices:
            snapshot_key = self._snapshot_key(user_id, int(idx_str))
            data = await self.redis.get(snapshot_key)  # type: ignore[misc]

            if data:
                snapshot_dict = json.loads(data)
                snapshots.append(TextSnapshot(
                    text=snapshot_dict["text"],
                    timestamp=datetime.fromisoformat(snapshot_dict["timestamp"]),
                    word_count=snapshot_dict["word_count"],
                ))

        return snapshots

    async def clear_user_snapshots(self, user_id: str) -> None:
        """Clear all snapshots for a user (privacy/testing)."""
        list_key = self._snapshot_list_key(user_id)
        indices = await self.redis.lrange(list_key, 0, -1)  # type: ignore[misc]

        # Delete all snapshot keys
        for idx_str in indices:
            snapshot_key = self._snapshot_key(user_id, int(idx_str))
            await self.redis.delete(snapshot_key)  # type: ignore[misc]

        # Delete list key
        await self.redis.delete(list_key)  # type: ignore[misc]

        logger.info("Cleared all snapshots for user %s", user_id)


async def get_snapshot_store() -> SnapshotStore:
    """Get snapshot store instance (dependency injection)."""
    redis_client = await get_redis()
    return SnapshotStore(redis_client)
