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

    if (now - this.lastSnapshotTime < SNAPSHOT_INTERVAL) {
      return null;
    }

    const snapshot: Snapshot = {
      id: `snapshot-${now}`,
      text,
      timestamp: now,
      wordCount: text.split(/\s+/).filter(Boolean).length,
    };

    this.snapshots.push(snapshot);
    this.lastSnapshotTime = now;

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

  getSnapshots(): Snapshot[] {
    return [...this.snapshots];
  }

  clear(): void {
    this.snapshots = [];
    this.lastSnapshotTime = 0;
  }
}

export const snapshotManager = new SnapshotManager();
