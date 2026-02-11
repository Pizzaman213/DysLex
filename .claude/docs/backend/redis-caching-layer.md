# Redis Caching Layer

## Purpose

Redis provides two services: generic cache (error profiles, API responses) and privacy-first snapshot storage for the passive learning loop.

## Implementation

`backend/app/services/redis_client.py`:

### Generic Cache Helpers

| Function | Purpose |
|----------|---------|
| `cache_get(key)` | JSON-deserialized cache read (returns None on miss/error) |
| `cache_set(key, value, ttl)` | JSON-serialized cache write |
| `cache_delete(key)` | Cache invalidation |

All functions **fail silently** — Redis being down never breaks the application.

### SnapshotStore

Redis-backed rolling window of text snapshots for passive learning:

```python
class SnapshotStore:
    async def save_snapshot(user_id, text, word_count)
    async def get_recent_snapshots(user_id, count=10)
    async def get_snapshot_pair(user_id)  # Last two for diffing
```

- Snapshots auto-expire after 24 hours (TTL)
- Used by the [adaptive loop](../core/adaptive-learning-loop.md) for diff processing
- Privacy: snapshots are ephemeral, never persisted to PostgreSQL

### Connection Pooling

Async Redis connection via `redis.asyncio` with connection pooling. Connection parameters from `backend/app/config.py`:

```python
redis_url: str = "redis://localhost:6379/0"
```

## Cache Consumers

| Consumer | Key Pattern | TTL | Purpose |
|----------|------------|-----|---------|
| Error Profile | `profile:{user_id}` | 10 min | Assembled profile cache |
| WebAuthn Challenge | `challenge:{challenge_id}` | 5 min | Passkey registration/login |
| Snapshots | `snapshots:{user_id}` | 24 hours | Passive learning |

## Key Files

| File | Role |
|------|------|
| `backend/app/services/redis_client.py` | Cache helpers + SnapshotStore |
| `backend/app/core/error_profile.py` | Uses cache for profile assembly |
| `backend/app/api/routes/passkey.py` | Uses cache for WebAuthn challenges |
| `backend/app/config.py` | Redis URL configuration |

## Integration Points

- [Error Profile](../core/error-profile-system.md): 10-min profile caching
- [Adaptive Loop](../core/adaptive-learning-loop.md): Snapshot storage
- [Passkey Auth](passkey-authentication.md): Challenge storage with TTL

## Status

- [x] Generic cache helpers (fail-safe)
- [x] SnapshotStore with TTL
- [x] Connection pooling
- [x] Integrated with error profile and passkey auth
