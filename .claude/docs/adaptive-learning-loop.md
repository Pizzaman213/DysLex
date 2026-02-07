# Adaptive Learning Loop

## Purpose

This is what makes DysLex AI different from every other writing tool. The system learns **passively** by observing what users naturally do — no accept/reject buttons, no pop-ups, no decisions to make.

**The core insight**: Forcing dyslexic users to evaluate corrections adds cognitive load and stigma. Instead, we silently watch their natural behavior and learn from it.

## User Experience

The user just writes. That's it.

- No "Accept" or "Reject" buttons
- No pop-up dialogs asking for feedback
- No visible indication that learning is happening
- The tool simply gets better over time

The user discovers their improvement when they choose to look at the progress dashboard — never forced on them.

## The Five Passive Signals

The system captures five types of behavioral signals without any user action:

### 1. Self-Correction
**What happens**: User goes back and fixes their own error ("teh" → "the")

**What we learn**: This is an error they make AND recognize. The system should catch it earlier next time to save them the effort.

**Action**: Increase priority in Quick Correction Model.

### 2. No Change Over Time
**What happens**: User leaves a flagged word alone across 3+ writing sessions

**What we learn**: This word might be intentional — a name, slang, technical term, creative spelling.

**Action**: Add to personal dictionary. Stop flagging.

### 3. Different Word Entirely
**What happens**: User rewrote a section and a word changed unexpectedly ("bark" → "park")

**What we learn**: This captures the user's true intent. The before/after pair is high-value training data.

**Action**: Log as correction pair. Update Error Profile.

### 4. Same Error Repeated
**What happens**: User writes "becuase" in 5 different documents over multiple sessions

**What we learn**: This is a high-frequency persistent error that the user doesn't self-correct.

**Action**: Prioritize in Quick Correction Model for instant catching.

### 5. Error Stops Appearing
**What happens**: User used to write "teh" regularly but hasn't done so in 2+ weeks

**What we learn**: They've internalized this correction. The learning worked.

**Action**: Reduce priority. Note improvement in progress dashboard.

## Technical Implementation

### Snapshot Engine (Frontend)

The frontend takes text snapshots:
- Every 5-10 seconds while actively typing
- Immediately when user pauses for 3+ seconds
- On blur (switching away from editor)

```typescript
// frontend/src/hooks/usePassiveLearning.ts
const takeSnapshot = useCallback((text: string) => {
  if (text === lastSnapshotRef.current) return;
  lastSnapshotRef.current = text;
  setSnapshots(prev => [...prev.slice(-10), { text, timestamp: Date.now() }]);
}, []);
```

### Diff Engine (Frontend)

Compares consecutive snapshots using word-level diff:

```typescript
// frontend/src/utils/diffEngine.ts
export function computeWordDiff(oldText: string, newText: string): DiffResult {
  // Returns: insertions, deletions, substitutions, reorderings
  // Substitutions are the most valuable signal
}
```

### Adaptive Loop Processor (Backend)

Processes diffs and updates Error Profile:

```python
# backend/app/core/adaptive_loop.py
async def process_snapshot_pair(before, after, user_id, db):
    corrections = detect_substitutions(before, after)
    for correction in corrections:
        await update_error_profile(user_id, correction, db)
```

### Error Profile Updates (Backend)

```python
# backend/app/core/error_profile.py
async def record_correction(user_id, original, corrected, error_type, db):
    # Update frequency map
    # Classify error type
    # Check for new confusion pairs
    # Update improvement tracking
```

## Key Files

### Frontend
- `frontend/src/hooks/usePassiveLearning.ts` — Snapshot management
- `frontend/src/utils/diffEngine.ts` — Word-level diff algorithm
- `frontend/src/utils/snapshotManager.ts` — Snapshot storage

### Backend
- `backend/app/core/adaptive_loop.py` — Main processing logic
- `backend/app/core/error_profile.py` — Profile updates
- `backend/app/db/repositories/error_pattern_repo.py` — Database access

### Database
- `error_logs` table — Individual correction records
- `error_profiles` table — Aggregated patterns (JSONB)
- `progress_snapshots` table — Weekly progress summaries

## Integration Points

- **Editor**: Triggers snapshots on text changes
- **Quick Correction Model**: Uses Error Profile for personalization
- **Deep Analysis LLM**: Receives Error Profile in prompt
- **Progress Dashboard**: Reads improvement data

## Accessibility Requirements

- **Zero cognitive load**: No decisions required
- **Zero stigma**: No visible "correction" UI
- **Zero friction**: Works like a normal editor
- **Privacy**: All learning data is per-user and private

## Why This Matters

Traditional spell checkers:
1. Show red underline
2. User right-clicks
3. User picks from suggestions
4. Repeat forever

DysLex AI:
1. User writes naturally
2. System learns silently
3. Corrections improve automatically
4. User notices they're making fewer errors

The second approach respects the user's intelligence and time.

## Status

- [x] Designed
- [x] Snapshot engine implemented
- [x] Diff engine implemented
- [x] Backend structure implemented
- [ ] Full integration tested
- [ ] Progress dashboard connected
