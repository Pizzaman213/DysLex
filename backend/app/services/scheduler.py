"""Background job scheduler for adaptive learning tasks.

Runs periodic jobs for:
- Daily signal detection (no-change words, progress snapshots)
- Nightly model retraining trigger (2:30 AM)
- Weekly improvement detection
- Daily data retention cleanup
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_all_user_ids() -> list[str]:
    """Open a standalone session and return all user IDs."""
    from app.db.database import async_session_factory
    from app.db.repositories import user_repo

    async with async_session_factory() as session:
        return await user_repo.get_all_user_ids(session)


# ---------------------------------------------------------------------------
# Job 1: No-Change Word Detection (Daily 2:00 AM)
# ---------------------------------------------------------------------------


async def detect_no_change_words_job() -> None:
    """Daily job: Detect words that users ignore after being flagged.

    Signal #2: No Change Over Time
    - Gets patterns with frequency >= 3 that the user never self-corrects
    - Auto-adds to personal dictionary (source="auto") after 3+ occurrences
    - Invalidates Redis cache for modified users
    """
    logger.info("Running daily no-change word detection job")

    from app.db.database import async_session_factory
    from app.db.repositories import personal_dictionary_repo, user_error_pattern_repo
    from app.services.redis_client import cache_delete

    try:
        user_ids = await _get_all_user_ids()
        total_words_added = 0
        users_modified = 0

        for user_id in user_ids:
            try:
                async with async_session_factory() as session:
                    # Get patterns with frequency >= 3
                    patterns = await user_error_pattern_repo.get_top_patterns(
                        session, user_id, limit=200,
                    )
                    high_freq = [p for p in patterns if p.frequency >= 3]

                    if not high_freq:
                        continue

                    # Get the user's personal dictionary
                    dictionary = await personal_dictionary_repo.get_dictionary(
                        session, user_id,
                    )
                    dict_words = {entry.word for entry in dictionary}

                    # Find misspellings that are NOT self-corrected (the user keeps
                    # writing them the same way) and NOT already in the dictionary.
                    # "Not self-corrected" heuristic: pattern.improving is False
                    # (they haven't reduced frequency) — they simply keep using
                    # this word, so it's likely intentional.
                    words_added = 0
                    for p in high_freq:
                        word = p.misspelling.lower()
                        if word in dict_words:
                            continue
                        # Only auto-add if the user is NOT improving on this pattern
                        # (i.e. they consistently write it — it's likely intentional)
                        if not p.improving:
                            await personal_dictionary_repo.add_word(
                                session, user_id, word, source="auto",
                            )
                            words_added += 1
                            dict_words.add(word)

                    if words_added > 0:
                        await session.commit()
                        await cache_delete(f"profile:{user_id}")
                        users_modified += 1
                        total_words_added += words_added

            except Exception:
                logger.error(
                    "No-change detection failed for user %s", user_id, exc_info=True,
                )

        logger.info(
            "No-change word detection completed: %d users processed, %d modified, %d words added",
            len(user_ids), users_modified, total_words_added,
        )
    except Exception:
        logger.error("Failed to run no-change word detection", exc_info=True)


# ---------------------------------------------------------------------------
# Job 2: Model Retraining Trigger (Daily 2:30 AM)
# ---------------------------------------------------------------------------


async def trigger_model_retraining_job() -> None:
    """Nightly job: Check if any user needs model retraining.

    Triggers retraining when a user has 50+ patterns updated in the last 7 days.
    Sets a Redis flag ``retrain_needed:{user_id}`` with 7-day TTL.
    Actual retraining is a separate ML pipeline concern.
    """
    logger.info("Running nightly model retraining check")

    from app.db.database import async_session_factory
    from app.db.repositories import user_error_pattern_repo
    from app.services.redis_client import get_redis

    try:
        user_ids = await _get_all_user_ids()
        flagged_count = 0
        since = datetime.now(UTC) - timedelta(days=7)

        for user_id in user_ids:
            try:
                async with async_session_factory() as session:
                    count = await user_error_pattern_repo.count_patterns_since(
                        session, user_id, since,
                    )

                if count >= 50:
                    redis = await get_redis()
                    await redis.setex(
                        f"retrain_needed:{user_id}",
                        timedelta(days=7),
                        "1",
                    )
                    flagged_count += 1
                    logger.info(
                        "User %s flagged for retraining (%d patterns in 7 days)",
                        user_id, count,
                    )

            except Exception:
                logger.error(
                    "Retraining check failed for user %s", user_id, exc_info=True,
                )

        logger.info(
            "Model retraining check completed: %d users processed, %d flagged",
            len(user_ids), flagged_count,
        )
    except Exception:
        logger.error("Failed to run model retraining check", exc_info=True)


# ---------------------------------------------------------------------------
# Job 3: Improvement Detection (Weekly Monday 3:00 AM)
# ---------------------------------------------------------------------------


async def detect_improvement_patterns_job() -> None:
    """Weekly job: Detect error patterns that have stopped appearing.

    Signal #5: Error Stops Appearing
    Reuses ``error_profile_service.detect_improvement()`` which compares the
    last 14-day window to the prior 14 days and bulk-marks patterns.
    """
    logger.info("Running weekly improvement pattern detection")

    from app.core.error_profile import error_profile_service
    from app.db.database import async_session_factory
    from app.services.redis_client import cache_delete

    try:
        user_ids = await _get_all_user_ids()
        total_improving = 0

        for user_id in user_ids:
            try:
                async with async_session_factory() as session:
                    result = await error_profile_service.detect_improvement(
                        user_id, session,
                    )
                    await session.commit()

                    improving = result.get("patterns_improving", 0)
                    if improving > 0:
                        await cache_delete(f"profile:{user_id}")
                        total_improving += improving

            except Exception:
                logger.error(
                    "Improvement detection failed for user %s", user_id, exc_info=True,
                )

        logger.info(
            "Improvement detection completed: %d users processed, %d patterns marked improving",
            len(user_ids), total_improving,
        )
    except Exception:
        logger.error("Failed to run improvement detection", exc_info=True)


# ---------------------------------------------------------------------------
# Job 4: Progress Snapshots (Weekly Monday 3:30 AM)
# ---------------------------------------------------------------------------


async def generate_progress_snapshots_job() -> None:
    """Weekly job: Generate progress snapshots for all active users.

    Reuses ``error_profile_service.generate_weekly_snapshot()`` which
    aggregates and upserts a ``ProgressSnapshot`` row.
    """
    logger.info("Running weekly progress snapshot generation")

    from app.core.error_profile import error_profile_service
    from app.db.database import async_session_factory

    try:
        user_ids = await _get_all_user_ids()
        generated = 0

        for user_id in user_ids:
            try:
                async with async_session_factory() as session:
                    await error_profile_service.generate_weekly_snapshot(
                        user_id, session,
                    )
                    await session.commit()
                    generated += 1

            except Exception:
                logger.error(
                    "Snapshot generation failed for user %s", user_id, exc_info=True,
                )

        logger.info(
            "Progress snapshot generation completed: %d/%d users",
            generated, len(user_ids),
        )
    except Exception:
        logger.error("Failed to generate progress snapshots", exc_info=True)


# ---------------------------------------------------------------------------
# Job 5: Data Retention Cleanup (Daily 3:00 AM)
# ---------------------------------------------------------------------------


async def cleanup_old_error_logs_job() -> None:
    """Daily job: Delete error_logs older than the retention period.

    Does NOT delete user_error_patterns (aggregated data) or
    progress_snapshots (already weekly aggregates).
    """
    from app.config import settings

    if not settings.retention_cleanup_enabled:
        logger.info("Data retention cleanup is disabled — skipping")
        return

    logger.info("Running data retention cleanup (retention=%d days)", settings.error_log_retention_days)

    from app.db.database import async_session_factory
    from app.db.repositories import error_log_repo

    try:
        user_ids = await _get_all_user_ids()
        cutoff = datetime.now(UTC) - timedelta(days=settings.error_log_retention_days)
        total_deleted = 0

        for user_id in user_ids:
            try:
                async with async_session_factory() as session:
                    deleted = await error_log_repo.delete_logs_before_date(
                        session, user_id, cutoff,
                    )
                    await session.commit()
                    total_deleted += deleted
            except Exception:
                logger.error(
                    "Retention cleanup failed for user %s", user_id, exc_info=True,
                )

        logger.info(
            "Data retention cleanup completed: %d logs deleted across %d users",
            total_deleted, len(user_ids),
        )
    except Exception:
        logger.error("Failed to run data retention cleanup", exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


def start_scheduler() -> AsyncIOScheduler:
    """Start the background job scheduler.

    Configures and starts APScheduler with all periodic jobs.
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    # Daily job at 2 AM: No-change word detection
    _scheduler.add_job(
        detect_no_change_words_job,
        CronTrigger(hour=2, minute=0),
        id="detect_no_change_words",
        name="Detect no-change words (Signal #2)",
        replace_existing=True,
    )

    # Daily job at 2:30 AM: Model retraining check
    _scheduler.add_job(
        trigger_model_retraining_job,
        CronTrigger(hour=2, minute=30),
        id="trigger_model_retraining",
        name="Trigger model retraining",
        replace_existing=True,
    )

    # Weekly job on Monday at 3 AM: Improvement pattern detection
    _scheduler.add_job(
        detect_improvement_patterns_job,
        CronTrigger(day_of_week="mon", hour=3, minute=0),
        id="detect_improvement_patterns",
        name="Detect improvement patterns (Signal #5)",
        replace_existing=True,
    )

    # Weekly job on Monday at 3:30 AM: Progress snapshots
    _scheduler.add_job(
        generate_progress_snapshots_job,
        CronTrigger(day_of_week="mon", hour=3, minute=30),
        id="generate_progress_snapshots",
        name="Generate weekly progress snapshots",
        replace_existing=True,
    )

    # Daily job at 3 AM: Data retention cleanup
    _scheduler.add_job(
        cleanup_old_error_logs_job,
        CronTrigger(hour=3, minute=0),
        id="cleanup_old_error_logs",
        name="Cleanup old error logs (retention)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Background scheduler started with %d jobs", len(_scheduler.get_jobs()))

    return _scheduler


def stop_scheduler() -> None:
    """Stop the background job scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Background scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the current scheduler instance."""
    return _scheduler


def trigger_job_now(job_id: str) -> bool:
    """Manually trigger a scheduled job immediately.

    Args:
        job_id: Job identifier (e.g., 'detect_no_change_words')

    Returns:
        True if job was triggered, False if job not found
    """
    if _scheduler is None:
        logger.error("Cannot trigger job - scheduler not running")
        return False

    job = _scheduler.get_job(job_id)
    if job is None:
        logger.error("Job not found: %s", job_id)
        return False

    job.modify(next_run_time=datetime.now())
    logger.info("Manually triggered job: %s", job_id)
    return True
