# Background Scheduler

APScheduler-based background job system for DysLex AI adaptive learning.

## Jobs

### Daily Jobs (2 AM)

#### 1. No-Change Word Detection
- **Job ID**: `detect_no_change_words`
- **Schedule**: Daily at 2:00 AM
- **Purpose**: Detect words flagged as errors that remain unchanged across 3+ sessions
- **Action**: Auto-add to personal dictionary
- **Signal**: #2 - No Change Over Time

#### 2. Model Retraining Check
- **Job ID**: `trigger_model_retraining`
- **Schedule**: Daily at 2:30 AM
- **Purpose**: Check if any user needs Quick Correction model retraining
- **Triggers When**:
  - User has 50+ new error pairs since last retrain
  - Last retrain was more than 7 days ago
- **Action**: Retrain user's Quick Correction adapter

### Weekly Jobs (Monday 3 AM)

#### 3. Improvement Pattern Detection
- **Job ID**: `detect_improvement_patterns`
- **Schedule**: Monday at 3:00 AM
- **Purpose**: Detect error patterns that have stopped appearing
- **Method**: Compare current 2-week window to previous 2 weeks
- **Action**: Mark patterns as 'improving' in database
- **Signal**: #5 - Error Stops Appearing

#### 4. Progress Snapshot Generation
- **Job ID**: `generate_progress_snapshots`
- **Schedule**: Monday at 3:30 AM
- **Purpose**: Generate weekly progress snapshots for all active users
- **Action**: Create aggregates for dashboard display

## Manual Triggering

### API Endpoint
```bash
POST /api/v1/learn/trigger-retrain
Authorization: Bearer <token>
```

### Programmatic
```python
from app.services.scheduler import trigger_job_now

# Trigger a specific job immediately
trigger_job_now("trigger_model_retraining")
```

## Configuration

Jobs are configured in `scheduler.py` using cron triggers:

```python
scheduler.add_job(
    job_function,
    CronTrigger(hour=2, minute=0),  # Daily at 2 AM
    id="job_id",
    name="Job Name",
    replace_existing=True,
)
```

## Lifecycle

The scheduler is managed by FastAPI's lifespan context:

```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()  # Start on app startup
    yield
    stop_scheduler()   # Stop on app shutdown
```

## Monitoring

### Check Running Jobs
```python
from app.services.scheduler import get_scheduler

scheduler = get_scheduler()
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"{job.id}: {job.name} - Next run: {job.next_run_time}")
```

### Logs
All job executions are logged:
```
INFO: Running daily no-change word detection job
INFO: No-change word detection completed (stub)
```

## Job Implementation Status

| Job | Status | Notes |
|-----|--------|-------|
| No-change word detection | ⚠️ Stub | Needs personal dictionary auto-add logic |
| Model retraining | ⚠️ Stub | Needs ML pipeline integration |
| Improvement detection | ⚠️ Stub | Needs 14-day window comparison |
| Progress snapshots | ⚠️ Stub | Needs aggregation logic |

All jobs are scheduled and running, but the actual implementation logic is placeholder code waiting for ML pipeline integration.

## Testing

### Run Job Immediately
```bash
# Trigger retrain job now (instead of waiting for 2:30 AM)
curl -X POST http://localhost:8000/api/v1/learn/trigger-retrain \
  -H "Authorization: Bearer <token>"
```

### Check Job Status
```bash
# Get learning stats (includes job execution info)
curl http://localhost:8000/api/v1/learn/stats/test_user \
  -H "Authorization: Bearer <token>"
```

## Dependencies

- `apscheduler>=3.10.0` (async scheduler)
- FastAPI lifespan events
- Async database access via SQLAlchemy

## Next Steps

1. Implement no-change word detection logic
2. Integrate Quick Correction Engine retraining pipeline
3. Add 14-day window comparison for improvement detection
4. Implement progress snapshot aggregation
5. Add job execution history tracking
6. Add alerting for failed jobs
