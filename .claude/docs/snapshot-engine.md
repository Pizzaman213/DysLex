# Snapshot Engine

## Purpose

The Snapshot Engine captures text state at regular intervals, enabling the passive learning loop to detect user self-corrections without explicit feedback.

**Key insight**: By comparing snapshots, we can see what the user changed — and learn from it silently.

## How It Works

1. User types in editor
2. Snapshot taken every 5-10 seconds
3. Additional snapshot on pause (3+ seconds)
4. Snapshots compared via diff engine
5. Self-corrections detected from substitutions
6. Error Profile updated silently

## Technical Implementation

### Snapshot Manager

```typescript
// frontend/src/utils/snapshotManager.ts
interface Snapshot {
  id: string;
  text: string;
  timestamp: number;
  wordCount: number;
}

const MAX_SNAPSHOTS = 50;
const SNAPSHOT_INTERVAL = 5000;

class SnapshotManager {
  private snapshots: Snapshot[] = [];
  private lastSnapshotTime = 0;

  addSnapshot(text: string): Snapshot | null {
    const now = Date.now();

    // Rate limit snapshots
    if (now - this.lastSnapshotTime < SNAPSHOT_INTERVAL) {
      return null;
    }

    const snapshot = {
      id: `snapshot-${now}`,
      text,
      timestamp: now,
      wordCount: text.split(/\s+/).filter(Boolean).length,
    };

    this.snapshots.push(snapshot);
    this.lastSnapshotTime = now;

    // Keep only recent snapshots
    if (this.snapshots.length > MAX_SNAPSHOTS) {
      this.snapshots.shift();
    }

    return snapshot;
  }

  getLastSnapshot(): Snapshot | null {
    return this.snapshots[this.snapshots.length - 1] || null;
  }

  getPreviousSnapshot(): Snapshot | null {
    return this.snapshots[this.snapshots.length - 2] || null;
  }
}
```

### Passive Learning Hook

```typescript
// frontend/src/hooks/usePassiveLearning.ts
export function usePassiveLearning() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const lastSnapshotRef = useRef<string>('');

  const takeSnapshot = useCallback((text: string) => {
    // Skip if text unchanged
    if (text === lastSnapshotRef.current) return;

    lastSnapshotRef.current = text;
    setSnapshots(prev => [...prev.slice(-10), { text, timestamp: Date.now() }]);
  }, []);

  const computeDiff = useCallback(() => {
    if (snapshots.length < 2) return;

    const previous = snapshots[snapshots.length - 2];
    const current = snapshots[snapshots.length - 1];

    const diff = computeWordDiff(previous.text, current.text);

    if (diff.changes.length > 0) {
      // Analyze user corrections
      analyzeUserCorrections(diff);
    }
  }, [snapshots]);

  return { takeSnapshot, computeDiff };
}
```

### Diff Engine

```typescript
// frontend/src/utils/diffEngine.ts
export interface DiffChange {
  type: 'add' | 'remove' | 'replace' | 'unchanged';
  oldValue?: string;
  newValue?: string;
  position: number;
}

export interface DiffResult {
  changes: DiffChange[];
  timestamp: number;
}

export function computeWordDiff(oldText: string, newText: string): DiffResult {
  const oldWords = tokenize(oldText);
  const newWords = tokenize(newText);

  // Use Longest Common Subsequence algorithm
  const lcs = longestCommonSubsequence(oldWords, newWords);

  const changes: DiffChange[] = [];
  // Compare against LCS to find insertions, deletions, substitutions

  return { changes, timestamp: Date.now() };
}

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}
```

## Snapshot Triggers

| Trigger | Interval | Purpose |
|---------|----------|---------|
| Typing | Every 5-10s | Capture ongoing work |
| Pause | After 3s idle | User may have just corrected |
| Blur | On focus loss | Capture final state |
| Save | On manual save | Definitive checkpoint |

## What Gets Detected

### Substitutions (Most Valuable)
```
Before: "I wnet to the store"
After:  "I went to the store"
Detected: "wnet" → "went" (self-correction)
```

### Deletions
```
Before: "I really really want"
After:  "I really want"
Detected: Removed duplicate "really"
```

### Insertions
```
Before: "I want go home"
After:  "I want to go home"
Detected: Inserted "to"
```

## Integration with Backend

When self-corrections are detected:

```typescript
async function analyzeUserCorrections(diff: DiffResult) {
  const substitutions = diff.changes.filter(c => c.type === 'replace');

  if (substitutions.length > 0) {
    // Send to backend for Error Profile update
    await api.reportUserCorrections(substitutions);
  }
}
```

## Key Files

### Frontend
- `frontend/src/utils/snapshotManager.ts` — Snapshot storage
- `frontend/src/utils/diffEngine.ts` — Word-level diff
- `frontend/src/hooks/usePassiveLearning.ts` — Main hook

### Backend
- `backend/app/core/adaptive_loop.py` — Processes diffs
- `backend/app/core/error_profile.py` — Updates profile

## Performance Considerations

- Snapshots stored in memory only (not persisted)
- Diff algorithm is O(n*m) — fast for typical text lengths
- Max 50 snapshots kept to limit memory
- Debounce to prevent excessive snapshots

## Privacy

- Snapshots never leave the device
- Only detected correction pairs sent to backend
- No raw text stored on server
- User can disable passive learning

## Status

- [x] Snapshot manager implemented
- [x] Diff engine implemented
- [x] usePassiveLearning hook created
- [ ] Backend integration complete
- [ ] Performance optimization
- [ ] Privacy controls UI
