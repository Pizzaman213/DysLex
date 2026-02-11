# Adaptive Learning Loop

## Purpose

The system learns passively by observing what users naturally do — no accept/reject buttons, no pop-ups, no decisions to make. See [CLAUDE.md > Adaptive Learning Loop](../../../CLAUDE.md) for the full design philosophy.

## Technical Implementation

### Snapshot Engine (Frontend)

Text snapshots are taken periodically and on pause. The `useSnapshotEngine` hook in DraftMode manages this:

- Every 5-10 seconds while actively typing
- On pause (3+ seconds)
- On blur (switching away from editor)

Snapshots are stored in Redis via the backend's `SnapshotStore` class (`backend/app/services/redis_client.py`) with 24-hour TTL.

### Adaptive Loop Processor (Backend)

`backend/app/core/adaptive_loop.py` processes snapshot pairs:

```python
async def process_snapshot_pair(before: str, after: str, user_id: str, db: AsyncSession):
    # Uses difflib for word-level changes
    # Levenshtein distance (0.3-0.95 range = likely correction)
    # Returns list of UserCorrection objects
```

**Error classification** (`_classify_error_type()`):
- Loads homophones from `ml/confusion_pairs/en.json`
- Detects reversals (b/d, p/q), phonetic patterns, omissions
- Falls back to generic "spelling" type

### Error Profile Updates

Detected corrections flow through `update_error_profile_from_corrections()` → `ErrorProfileService.log_error()` which:
1. Inserts into `error_logs` table
2. Upserts `user_error_patterns` (frequency tracking)
3. Updates confusion pairs if applicable

### Background Jobs (Scheduler)

Five scheduled jobs in `backend/app/services/scheduler.py` complete the loop:

| Job | Schedule | Purpose |
|-----|----------|---------|
| `detect_no_change_words` | Daily 2 AM | Auto-add to personal dictionary |
| `trigger_model_retraining` | Daily 2:30 AM | Flag users with 50+ new patterns |
| `detect_improvement_patterns` | Weekly Mon 3 AM | Mark patterns as improving |
| `generate_progress_snapshots` | Weekly Mon 3:30 AM | Aggregate weekly stats |
| `cleanup_old_error_logs` | Daily 3 AM | Delete logs past retention (90 days) |

## Key Files

| Component | File | Key Function |
|-----------|------|-------------|
| Snapshot storage | `backend/app/services/redis_client.py` | `SnapshotStore` class |
| Diff processor | `backend/app/core/adaptive_loop.py` | `process_snapshot_pair()` |
| Profile updates | `backend/app/core/error_profile.py` | `ErrorProfileService.log_error()` |
| Pattern repo | `backend/app/db/repositories/user_error_pattern_repo.py` | `upsert_pattern()` |
| Scheduler | `backend/app/services/scheduler.py` | 5 cron jobs |
| Frontend hook | `frontend/src/components/WritingModes/DraftMode.tsx` | `useSnapshotEngine` integration |

## Integration Points

- [Editor](../frontend/tiptap-editor.md): Triggers snapshots on text changes
- [Error Profile](error-profile-system.md): Updated with detected corrections
- [Background Scheduler](../backend/background-scheduler.md): Runs periodic learning jobs
- [Redis](../backend/redis-caching-layer.md): Stores snapshots with TTL

## Status

- [x] Snapshot engine with Redis storage
- [x] Diff engine with Levenshtein similarity
- [x] Error classification (reversals, homophones, phonetic, omissions)
- [x] Profile update pipeline
- [x] 5 background scheduler jobs
- [ ] Full end-to-end integration tested
- [ ] Progress dashboard connected to learning signals
