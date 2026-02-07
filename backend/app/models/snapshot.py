"""Snapshot and learning-stats Pydantic models."""

from datetime import datetime

from pydantic import BaseModel


class SnapshotRequest(BaseModel):
    """Text snapshot submitted by the frontend."""

    text: str
    document_id: str | None = None
    timestamp: datetime | None = None


class SnapshotResponse(BaseModel):
    """Acknowledgement after processing a snapshot."""

    received: bool = True
    signals_detected: int = 0


class LearnStats(BaseModel):
    """Summary of adaptive learning activity."""

    signals_captured: int = 0
    patterns_updated: int = 0
    last_retrain: datetime | None = None
