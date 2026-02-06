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
  const changes: DiffChange[] = [];

  const lcs = longestCommonSubsequence(oldWords, newWords);
  let oldIdx = 0;
  let newIdx = 0;
  let lcsIdx = 0;

  while (oldIdx < oldWords.length || newIdx < newWords.length) {
    if (lcsIdx < lcs.length && oldIdx < oldWords.length && oldWords[oldIdx] === lcs[lcsIdx]) {
      if (newIdx < newWords.length && newWords[newIdx] === lcs[lcsIdx]) {
        oldIdx++;
        newIdx++;
        lcsIdx++;
      } else {
        changes.push({
          type: 'add',
          newValue: newWords[newIdx],
          position: newIdx,
        });
        newIdx++;
      }
    } else if (lcsIdx < lcs.length && newIdx < newWords.length && newWords[newIdx] === lcs[lcsIdx]) {
      changes.push({
        type: 'remove',
        oldValue: oldWords[oldIdx],
        position: oldIdx,
      });
      oldIdx++;
    } else if (oldIdx < oldWords.length && newIdx < newWords.length) {
      changes.push({
        type: 'replace',
        oldValue: oldWords[oldIdx],
        newValue: newWords[newIdx],
        position: oldIdx,
      });
      oldIdx++;
      newIdx++;
    } else if (oldIdx < oldWords.length) {
      changes.push({
        type: 'remove',
        oldValue: oldWords[oldIdx],
        position: oldIdx,
      });
      oldIdx++;
    } else if (newIdx < newWords.length) {
      changes.push({
        type: 'add',
        newValue: newWords[newIdx],
        position: newIdx,
      });
      newIdx++;
    }
  }

  return {
    changes,
    timestamp: Date.now(),
  };
}

function tokenize(text: string): string[] {
  return text.split(/\s+/).filter(Boolean);
}

function longestCommonSubsequence(a: string[], b: string[]): string[] {
  const dp: number[][] = Array(a.length + 1)
    .fill(null)
    .map(() => Array(b.length + 1).fill(0));

  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const result: string[] = [];
  let i = a.length;
  let j = b.length;

  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      result.unshift(a[i - 1]);
      i--;
      j--;
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  return result;
}
