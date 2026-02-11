# Snapshot Engine

## Purpose

Captures text state at regular intervals, enabling the passive learning loop to detect user self-corrections without explicit feedback.

## How It Works

1. User types in editor (DraftMode)
2. `useSnapshotEngine` hook takes snapshots every 5-10 seconds + on pause (3s)
3. Snapshots sent to backend → stored in Redis (`SnapshotStore`)
4. `adaptive_loop.py` diffs consecutive snapshots
5. Self-corrections detected and logged to Error Profile

## Frontend

The snapshot engine is integrated directly in `DraftMode.tsx` via `useSnapshotEngine`. Snapshots contain:
- Full text content
- Timestamp
- Word count

## Backend Processing

`backend/app/core/adaptive_loop.py`:

```python
async def process_snapshot_pair(before: str, after: str, user_id: str, db):
    # Uses difflib for word-level changes
    # Levenshtein distance (0.3-0.95 range = likely correction)
    # Returns list of UserCorrection objects with classification
```

### Detection

| Change Type | Signal | What We Learn |
|-------------|--------|---------------|
| Substitution | `"teh" → "the"` | Self-correction — catch earlier next time |
| Deletion | Removed duplicate word | User cleaning up |
| Insertion | Added missing word | Grammar awareness |

## Storage

Snapshots stored in Redis via `SnapshotStore` (`backend/app/services/redis_client.py`):
- Rolling window per user
- 24-hour TTL (ephemeral, privacy-first)
- Never persisted to PostgreSQL

## Key Files

| File | Role |
|------|------|
| `frontend/src/components/WritingModes/DraftMode.tsx` | `useSnapshotEngine` integration |
| `backend/app/core/adaptive_loop.py` | Snapshot diff processing |
| `backend/app/services/redis_client.py` | `SnapshotStore` class |
| `backend/app/core/error_profile.py` | Receives detected corrections |

## Integration Points

- [Adaptive Loop](../core/adaptive-learning-loop.md): Main consumer of snapshot diffs
- [Redis](redis-caching-layer.md): Ephemeral snapshot storage
- [Error Profile](../core/error-profile-system.md): Updated with detected corrections

## Status

- [x] Frontend snapshot taking (periodic + on-pause)
- [x] Redis-backed storage with TTL
- [x] Diff engine with Levenshtein similarity
- [x] Error classification
- [ ] Performance optimization for very long documents
