export interface DiffChange {
  type: 'add' | 'remove' | 'replace' | 'unchanged';
  oldValue?: string;
  newValue?: string;
  position: number;
  context?: string;
  category?: 'insertion' | 'deletion' | 'substitution' | 'reordering';
}

export interface DiffResult {
  changes: DiffChange[];
  timestamp: number;
}

// Enhanced types for passive learning
export type DiffSignal =
  | 'self-correction'   // User fixed their own typo
  | 'rewrite'          // User rewrote phrase completely
  | 'insertion'        // User added new text
  | 'deletion'         // User removed text
  | 'no-change';       // No meaningful change

export interface EnhancedDiffChange extends DiffChange {
  signal: DiffSignal;
  similarity?: number;
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

export function computeWordDiffWithContext(
  oldText: string,
  newText: string
): DiffResult {
  const baseResult = computeWordDiff(oldText, newText);

  // Enhance each change with context and category
  const enhancedChanges = baseResult.changes.map((change) => {
    const context = extractContext(oldText, change.position, 50);
    const category = categorizeChange(change);

    return {
      ...change,
      context,
      category,
    };
  });

  return {
    ...baseResult,
    changes: enhancedChanges,
  };
}

function extractContext(text: string, wordPosition: number, charLimit: number): string {
  const words = text.split(/\s+/).filter(Boolean);

  // Get surrounding words
  const startIdx = Math.max(0, wordPosition - 5);
  const endIdx = Math.min(words.length, wordPosition + 6);
  const contextWords = words.slice(startIdx, endIdx);

  let context = contextWords.join(' ');

  // Truncate if needed
  if (context.length > charLimit) {
    context = context.substring(0, charLimit) + '...';
  }

  return context;
}

function categorizeChange(change: DiffChange): 'insertion' | 'deletion' | 'substitution' | 'reordering' {
  switch (change.type) {
    case 'add':
      return 'insertion';
    case 'remove':
      return 'deletion';
    case 'replace':
      // Check if it's likely a reordering (similar words)
      if (change.oldValue && change.newValue) {
        const similarity = calculateSimilarity(change.oldValue, change.newValue);
        if (similarity < 0.3) {
          return 'reordering';
        }
      }
      return 'substitution';
    default:
      return 'substitution';
  }
}

function calculateSimilarity(a: string, b: string): number {
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 1.0;

  const distance = levenshteinDistance(a.toLowerCase(), b.toLowerCase());
  return 1.0 - distance / maxLen;
}

function levenshteinDistance(a: string, b: string): number {
  const matrix: number[][] = [];

  for (let i = 0; i <= b.length; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= a.length; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= b.length; i++) {
    for (let j = 1; j <= a.length; j++) {
      if (b.charAt(i - 1) === a.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        );
      }
    }
  }

  return matrix[b.length][a.length];
}

/**
 * Categorize a change as a specific signal for passive learning
 */
function categorizeSignal(change: DiffChange): DiffSignal {
  if (change.type === 'add') return 'insertion';
  if (change.type === 'remove') return 'deletion';

  if (change.type === 'replace' && change.oldValue && change.newValue) {
    const similarity = calculateSimilarity(change.oldValue, change.newValue);

    // High similarity (>60%) = self-correction
    // Low similarity = rewrite
    return similarity > 0.6 ? 'self-correction' : 'rewrite';
  }

  return 'no-change';
}

/**
 * Enhanced diff with signal categorization for passive learning
 */
export function computeEnhancedDiff(
  oldText: string,
  newText: string
): { changes: EnhancedDiffChange[]; timestamp: number } {
  const basicDiff = computeWordDiffWithContext(oldText, newText);

  const enhancedChanges = basicDiff.changes.map(change => {
    const signal = categorizeSignal(change);
    const similarity = change.oldValue && change.newValue
      ? calculateSimilarity(change.oldValue, change.newValue)
      : undefined;

    return {
      ...change,
      signal,
      similarity,
    };
  });

  return {
    changes: enhancedChanges,
    timestamp: basicDiff.timestamp,
  };
}
