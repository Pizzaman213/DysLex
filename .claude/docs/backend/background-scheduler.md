# Background Scheduler

## Purpose

APScheduler-based background job system that powers passive learning and data maintenance. Runs 5 jobs that complete the adaptive learning loop without user interaction.

## Jobs

`backend/app/services/scheduler.py`:

| Job | Schedule | Purpose |
|-----|----------|---------|
| `detect_no_change_words_job` | Daily 2:00 AM | Auto-add frequently ignored words to personal dictionary |
| `trigger_model_retraining_job` | Daily 2:30 AM | Flag users with 50+ new patterns in 7 days for retraining |
| `detect_improvement_patterns_job` | Weekly Mon 3:00 AM | Mark patterns as "improving" (not seen in 14+ days) |
| `generate_progress_snapshots_job` | Weekly Mon 3:30 AM | Generate weekly aggregated progress stats |
| `cleanup_old_error_logs_job` | Daily 3:00 AM | Delete error logs past retention period (90 days) |

### Job Details

**detect_no_change_words**: Queries patterns flagged 3+ times but never corrected by the user → adds to `personal_dictionary` so the system stops flagging them.

**trigger_model_retraining**: Finds users with high pattern activity → flags them for ONNX adapter retraining (future: actually retrain).

**detect_improvement_patterns**: Uses `user_error_pattern_repo.bulk_mark_improving()` to flag patterns where `last_seen` is 14+ days ago.

**generate_progress_snapshots**: Calls `ErrorProfileService.generate_weekly_snapshot()` per user → writes to `progress_snapshots` table.

**cleanup_old_error_logs**: Deletes `error_logs` records older than `settings.data_retention_days` (default: 90).

## Error Handling

All jobs catch exceptions per-user — one user's failure doesn't block others. Jobs log warnings but never crash the scheduler.

## Startup

`start_scheduler()` is called from `backend/app/main.py` lifespan event.

## Key Files

| File | Role |
|------|------|
| `backend/app/services/scheduler.py` | All 5 job definitions + `start_scheduler()` |
| `backend/app/core/error_profile.py` | `generate_weekly_snapshot()` |
| `backend/app/db/repositories/user_error_pattern_repo.py` | `bulk_mark_improving()`, `count_patterns_since()` |
| `backend/app/config.py` | `data_retention_days` setting |
| `backend/tests/test_scheduler_jobs.py` | Job tests |

## Integration Points

- [Adaptive Loop](../core/adaptive-learning-loop.md): Scheduler completes the learning cycle
- [Error Profile](../core/error-profile-system.md): Weekly snapshots + dictionary updates
- [Database](database-schema.md): Reads/writes pattern and progress tables

## Status

- [x] 5 scheduled jobs implemented
- [x] Per-user error isolation
- [x] APScheduler integration
- [x] Startup from FastAPI lifespan
- [ ] Per-user ONNX adapter retraining (currently just flags)
