"""Tests for adaptive learning loop."""

import pytest
from datetime import datetime

from app.core.adaptive_loop import TextSnapshot, process_snapshot_pair


@pytest.mark.asyncio
async def test_process_snapshot_pair():
    """Test processing snapshot pairs for corrections."""
    before = TextSnapshot(
        text="Teh quick brown fox",
        timestamp=datetime.now(),
        word_count=4,
    )
    after = TextSnapshot(
        text="The quick brown fox",
        timestamp=datetime.now(),
        word_count=4,
    )

    corrections = await process_snapshot_pair(before, after, "test-user", None)
    # Would verify correction detection
    assert isinstance(corrections, list)
