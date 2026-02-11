"""Tests for the adaptive learning scheduler jobs."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pattern(
    misspelling: str = "teh",
    correction: str = "the",
    frequency: int = 5,
    improving: bool = False,
    last_seen: datetime | None = None,
):
    """Create a mock UserErrorPattern."""
    p = MagicMock()
    p.misspelling = misspelling
    p.correction = correction
    p.frequency = frequency
    p.improving = improving
    p.last_seen = last_seen or datetime.now(timezone.utc)
    p.id = f"pattern-{misspelling}"
    return p


class FakeSession:
    """Minimal async context-manager that acts like AsyncSession."""

    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Job 1: detect_no_change_words_job
# ---------------------------------------------------------------------------


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_no_change_words_adds_to_dictionary(mock_ids):
    from app.services.scheduler import detect_no_change_words_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()

    patterns = [_make_pattern("becuase", "because", frequency=5, improving=False)]

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.db.repositories.user_error_pattern_repo.get_top_patterns",
            new_callable=AsyncMock,
            return_value=patterns,
        ),
        patch(
            "app.db.repositories.personal_dictionary_repo.get_dictionary",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.db.repositories.personal_dictionary_repo.add_word",
            new_callable=AsyncMock,
        ) as mock_add,
        patch("app.services.redis_client.cache_delete", new_callable=AsyncMock),
    ):
        await detect_no_change_words_job()

        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args[0][1] == "user-1"
        assert call_args[0][2] == "becuase"


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_no_change_words_skips_self_corrected(mock_ids):
    from app.services.scheduler import detect_no_change_words_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()

    # This pattern IS improving — user is self-correcting, so skip it
    patterns = [_make_pattern("teh", "the", frequency=10, improving=True)]

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.db.repositories.user_error_pattern_repo.get_top_patterns",
            new_callable=AsyncMock,
            return_value=patterns,
        ),
        patch(
            "app.db.repositories.personal_dictionary_repo.get_dictionary",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.db.repositories.personal_dictionary_repo.add_word",
            new_callable=AsyncMock,
        ) as mock_add,
        patch("app.services.redis_client.cache_delete", new_callable=AsyncMock),
    ):
        await detect_no_change_words_job()
        mock_add.assert_not_called()


# ---------------------------------------------------------------------------
# Job 2: trigger_model_retraining_job
# ---------------------------------------------------------------------------


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_retraining_sets_flag_when_threshold_met(mock_ids):
    from app.services.scheduler import trigger_model_retraining_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()
    mock_redis = AsyncMock()

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.db.repositories.user_error_pattern_repo.count_patterns_since",
            new_callable=AsyncMock,
            return_value=60,
        ),
        patch(
            "app.services.redis_client.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
    ):
        await trigger_model_retraining_job()

        mock_redis.setex.assert_called_once()
        key = mock_redis.setex.call_args[0][0]
        assert key == "retrain_needed:user-1"


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_retraining_skips_below_threshold(mock_ids):
    from app.services.scheduler import trigger_model_retraining_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()
    mock_redis = AsyncMock()

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.db.repositories.user_error_pattern_repo.count_patterns_since",
            new_callable=AsyncMock,
            return_value=10,
        ),
        patch(
            "app.services.redis_client.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ),
    ):
        await trigger_model_retraining_job()
        mock_redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# Job 3: detect_improvement_patterns_job
# ---------------------------------------------------------------------------


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_improvement_detection_calls_service(mock_ids):
    from app.services.scheduler import detect_improvement_patterns_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.core.error_profile.error_profile_service.detect_improvement",
            new_callable=AsyncMock,
            return_value={"trend": "improving", "patterns_improving": 3},
        ) as mock_detect,
        patch("app.services.redis_client.cache_delete", new_callable=AsyncMock),
    ):
        await detect_improvement_patterns_job()

        mock_detect.assert_called_once()
        assert session.committed


# ---------------------------------------------------------------------------
# Job 4: generate_progress_snapshots_job
# ---------------------------------------------------------------------------


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_snapshot_generation_calls_service(mock_ids):
    from app.services.scheduler import generate_progress_snapshots_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.core.error_profile.error_profile_service.generate_weekly_snapshot",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ) as mock_gen,
    ):
        await generate_progress_snapshots_job()

        mock_gen.assert_called_once()
        assert session.committed


# ---------------------------------------------------------------------------
# Job 5: cleanup_old_error_logs_job
# ---------------------------------------------------------------------------


@patch("app.services.scheduler._get_all_user_ids", new_callable=AsyncMock)
async def test_cleanup_deletes_old_logs(mock_ids):
    from app.services.scheduler import cleanup_old_error_logs_job

    mock_ids.return_value = ["user-1"]
    session = FakeSession()

    with (
        patch("app.db.database.async_session_factory", return_value=session),
        patch(
            "app.db.repositories.error_log_repo.delete_logs_before_date",
            new_callable=AsyncMock,
            return_value=25,
        ) as mock_delete,
        patch("app.config.settings.retention_cleanup_enabled", True),
        patch("app.config.settings.error_log_retention_days", 90),
    ):
        await cleanup_old_error_logs_job()

        mock_delete.assert_called_once()
        assert session.committed
