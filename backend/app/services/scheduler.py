"""Background job scheduler for adaptive learning tasks.

Runs periodic jobs for:
- Daily signal detection (no-change words, progress snapshots)
- Nightly model retraining (2 AM)
- Weekly improvement detection
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def detect_no_change_words_job() -> None:
    """Daily job: Detect words that users ignore after being flagged.

    Signal #2: No Change Over Time
    - Tracks words flagged as errors that remain unchanged across 3+ sessions
    - Auto-adds to personal dictionary after 3+ occurrences
    """
    logger.info("Running daily no-change word detection job")

    try:
        # TODO: Implement when personal dictionary auto-add logic is ready
        # For now, this is a placeholder
        logger.info("No-change word detection completed (stub)")
    except Exception:
        logger.error("Failed to run no-change word detection", exc_info=True)


async def trigger_model_retraining_job() -> None:
    """Nightly job: Check if any user needs model retraining.

    Triggers retraining when:
    - User has 50+ new error pairs since last retrain
    - Last retrain was more than 7 days ago
    """
    logger.info("Running nightly model retraining check")

    try:
        # TODO: Implement when Quick Correction Engine retraining pipeline is ready
        # For now, this is a placeholder
        logger.info("Model retraining check completed (stub)")
    except Exception:
        logger.error("Failed to run model retraining check", exc_info=True)


async def detect_improvement_patterns_job() -> None:
    """Weekly job: Detect error patterns that have stopped appearing.

    Signal #5: Error Stops Appearing
    - Compares current 2-week window to previous 2 weeks
    - Marks patterns as 'improving' if frequency drops significantly
    """
    logger.info("Running weekly improvement pattern detection")

    try:
        # TODO: Implement comprehensive improvement detection
        # For now, this is a placeholder
        logger.info("Improvement pattern detection completed (stub)")
    except Exception:
        logger.error("Failed to run improvement detection", exc_info=True)


async def generate_progress_snapshots_job() -> None:
    """Weekly job: Generate progress snapshots for all active users.

    Creates weekly aggregates for dashboard display.
    """
    logger.info("Running weekly progress snapshot generation")

    try:
        # TODO: Implement when progress snapshot generation is ready
        # For now, this is a placeholder
        logger.info("Progress snapshot generation completed (stub)")
    except Exception:
        logger.error("Failed to generate progress snapshots", exc_info=True)


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
