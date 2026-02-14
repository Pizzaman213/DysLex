"""Adaptive learning — snapshot submission endpoints."""

from datetime import datetime, timezone

UTC = timezone.utc

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUserId, DbSession
from app.core.adaptive_loop import TextSnapshot, process_snapshot_pair
from app.models.envelope import success_response
from app.models.snapshot import SnapshotRequest
from app.services.redis_client import SnapshotStore, get_snapshot_store

router = APIRouter()


@router.post("/snapshots")
async def submit_snapshot(
    body: SnapshotRequest,
    user_id: CurrentUserId,
    db: DbSession,
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
) -> dict:
    """Accept a text snapshot and diff against the previous one.

    Snapshots are stored in Redis with 24-hour TTL for privacy.
    Compares against previous snapshot to detect self-corrections.
    """
    now = body.timestamp or datetime.now(UTC)
    current = TextSnapshot(
        text=body.text,
        timestamp=now,
        word_count=len(body.text.split()),
    )

    signals = 0
    previous = await snapshot_store.get_last_snapshot(user_id)
    if previous is not None:
        corrections = await process_snapshot_pair(previous, current, user_id, db)
        signals = len(corrections)

    # Store current snapshot for future comparison
    await snapshot_store.store_snapshot(user_id, current)

    return success_response({"received": True, "signals_detected": signals})


@router.get("/snapshots/{user_id}/recent")
async def recent_snapshots(
    user_id: str,
    current_user: CurrentUserId,
    db: DbSession,
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
    limit: int = 5,
) -> dict:
    """Return recent snapshots for a user (dev/debug).

    Useful for debugging snapshot capture and diff detection.
    """
    snapshots = await snapshot_store.get_recent_snapshots(user_id, limit=limit)

    if not snapshots:
        return success_response({"snapshots": []})

    return success_response({
        "snapshots": [
            {
                "text": snap.text[:100] + "..." if len(snap.text) > 100 else snap.text,
                "timestamp": snap.timestamp.isoformat(),
                "word_count": snap.word_count,
            }
            for snap in snapshots
        ]
    })


@router.delete("/snapshots")
async def clear_snapshots(
    user_id: CurrentUserId,
    snapshot_store: SnapshotStore = Depends(get_snapshot_store),
) -> dict:
    """Clear all snapshots for current user (privacy control)."""
    await snapshot_store.clear_user_snapshots(user_id)
    return success_response({"cleared": True})
