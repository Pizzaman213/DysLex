/**
 * SymSpell + Phonetic Correction Service
 *
 * Provides two fallback tiers for when the dictionary lookup misses:
 *   Tier 2: SymSpell-style edit-distance lookup (Damerau-Levenshtein, max distance 2)
 *   Tier 3: Double Metaphone phonetic matching (sound-alike words)
 *
 * Uses a deletion-based index (SymSpell algorithm) for fast edit-distance
 * lookups and the double-metaphone package for phonetic encoding.
 *
 * Performance budget: <500ms init (one-time), <1ms per lookup, ~5MB memory.
 */

import { doubleMetaphone } from 'double-metaphone';

const MODEL_PATH = '/models/quick_correction_base_v1';
const MAX_EDIT_DISTANCE = 2;

/** Word + frequency from the dictionary */
interface DictEntry {
  word: string;
  freq: number;
}

/** Internal state */
let initialized = false;
let initializing = false;

// SymSpell deletion index: deletion variant -> list of original words with frequencies
const deletionIndex = new Map<string, DictEntry[]>();

// Full dictionary: word -> frequency (for validation and frequency ranking)
const wordFrequency = new Map<string, number>();

// Phonetic index: metaphone code -> list of words with frequencies
const phoneticIndex = new Map<string, DictEntry[]>();

// Result caches (bounded to prevent unbounded memory growth)
const MAX_CACHE_SIZE = 10_000;
const symspellCache = new Map<string, string | null>();
const phoneticCache = new Map<string, string | null>();

/**
 * Generate all deletion variants of a word up to maxDistance deletes.
 */
function generateDeletes(word: string, maxDistance: number): Set<string> {
  const deletes = new Set<string>();
  const queue: Array<{ w: string; d: number }> = [{ w: word, d: 0 }];

  while (queue.length > 0) {
    const { w, d } = queue.pop()!;
    if (d < maxDistance) {
      for (let i = 0; i < w.length; i++) {
        const deleted = w.slice(0, i) + w.slice(i + 1);
        if (!deletes.has(deleted)) {
          deletes.add(deleted);
          queue.push({ w: deleted, d: d + 1 });
        }
      }
    }
  }

  return deletes;
}

/**
 * Compute Damerau-Levenshtein distance between two strings.
 * Returns early if distance exceeds maxDistance.
 */
function damerauLevenshtein(a: string, b: string, maxDistance: number): number {
  const lenA = a.length;
  const lenB = b.length;

  // Quick length-based rejection
  if (Math.abs(lenA - lenB) > maxDistance) return maxDistance + 1;

  // Short-circuit for identical strings
  if (a === b) return 0;

  // Use a flat array instead of 2D for performance
  const d = new Array((lenA + 1) * (lenB + 1));
  const cols = lenB + 1;

  for (let i = 0; i <= lenA; i++) d[i * cols] = i;
  for (let j = 0; j <= lenB; j++) d[j] = j;

  for (let i = 1; i <= lenA; i++) {
    let minInRow = maxDistance + 1;
    for (let j = 1; j <= lenB; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let val = Math.min(
        d[(i - 1) * cols + j] + 1,       // deletion
        d[i * cols + (j - 1)] + 1,       // insertion
        d[(i - 1) * cols + (j - 1)] + cost // substitution
      );
      // Transposition
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        val = Math.min(val, d[(i - 2) * cols + (j - 2)] + cost);
      }
      d[i * cols + j] = val;
      if (val < minInRow) minInRow = val;
    }
    // Early termination: if no cell in this row is within maxDistance, abort
    if (minInRow > maxDistance) return maxDistance + 1;
  }

  return d[lenA * cols + lenB];
}

/**
 * Initialize the SymSpell index and phonetic index from the frequency dictionary.
 * Called once during model loading.
 */
export async function initSymSpell(): Promise<void> {
  if (initialized || initializing) return;
  initializing = true;

  try {
    const startTime = performance.now();

    // Fetch the frequency dictionary
    // Try full dictionary first (379K words), fall back to 82K if unavailable
    let response = await fetch(`${MODEL_PATH}/frequency_dictionary_en_full.txt`);
    if (!response.ok) {
      response = await fetch(`${MODEL_PATH}/frequency_dictionary_en_82_765.txt`);
    }
    if (!response.ok) {
      throw new Error(`Failed to fetch frequency dictionary: ${response.status}`);
    }

    const text = await response.text();
    const lines = text.split('\n');
    let wordCount = 0;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const spaceIdx = trimmed.lastIndexOf(' ');
      if (spaceIdx === -1) continue;

      const word = trimmed.slice(0, spaceIdx).toLowerCase();
      const freq = parseInt(trimmed.slice(spaceIdx + 1), 10);

      if (!word || isNaN(freq)) continue;
      // Skip single-character entries except common ones
      if (word.length === 1 && word !== 'a' && word !== 'i') continue;

      wordFrequency.set(word, freq);
      wordCount++;

      // Only build the expensive deletion + phonetic indexes for words with
      // real frequency data (freq > 1). Words with freq=1 are from the
      // supplementary Webster's dictionary — they're valid English but too
      // obscure to suggest as corrections. They still count for isKnownWord().
      if (freq <= 1) continue;

      // Build deletion index only for words <=15 chars (longer words generate
      // too many deletion variants and are rarely misspelled in common writing).
      if (word.length <= 15) {
        const deletes = generateDeletes(word, MAX_EDIT_DISTANCE);
        for (const del of deletes) {
          let entries = deletionIndex.get(del);
          if (!entries) {
            entries = [];
            deletionIndex.set(del, entries);
          }
          entries.push({ word, freq });
        }
      }

      // Build phonetic index (only for words 2+ chars)
      if (word.length >= 2) {
        const [primary, alternate] = doubleMetaphone(word);
        if (primary) {
          let entries = phoneticIndex.get(primary);
          if (!entries) {
            entries = [];
            phoneticIndex.set(primary, entries);
          }
          entries.push({ word, freq });
        }
        if (alternate && alternate !== primary) {
          let entries = phoneticIndex.get(alternate);
          if (!entries) {
            entries = [];
            phoneticIndex.set(alternate, entries);
          }
          entries.push({ word, freq });
        }
      }
    }

    const elapsed = performance.now() - startTime;
    console.log(`[SymSpell] Loaded ${wordCount} words in ${elapsed.toFixed(0)}ms`);
    console.log(`[SymSpell] Deletion index: ${deletionIndex.size} entries`);
    console.log(`[SymSpell] Phonetic index: ${phoneticIndex.size} entries`);

    initialized = true;
  } catch (error) {
    console.warn('[SymSpell] Initialization failed:', error);
  } finally {
    initializing = false;
  }
}

/**
 * Check if SymSpell has been initialized successfully.
 */
export function isSymSpellReady(): boolean {
  return initialized;
}

/**
 * Check if a word is a known valid English word.
 */
export function isKnownWord(word: string): boolean {
  return wordFrequency.has(word.toLowerCase());
}

/**
 * SymSpell edit-distance lookup.
 * Generates deletion variants of the input word, looks them up in the
 * pre-computed deletion index, then verifies candidates with true
 * Damerau-Levenshtein distance.
 *
 * Returns the highest-frequency suggestion within edit distance 2, or null.
 */
export function suggestCorrection(word: string): string | null {
  if (!initialized) return null;

  const lower = word.toLowerCase();

  // Check cache
  if (symspellCache.has(lower)) return symspellCache.get(lower)!;

  // If the word is in the dictionary, it's correct — no suggestion needed
  if (wordFrequency.has(lower)) {
    symspellCache.set(lower, null);
    return null;
  }

  // Generate deletion variants of the input (misspelled) word
  const inputDeletes = generateDeletes(lower, MAX_EDIT_DISTANCE);
  // Also check the word itself (for words that are a deletion of a dictionary word)
  inputDeletes.add(lower);

  let bestWord: string | null = null;
  let bestFreq = -1;
  let bestDist = MAX_EDIT_DISTANCE + 1;

  // Check each deletion variant against the index
  for (const variant of inputDeletes) {
    const candidates = deletionIndex.get(variant);
    if (!candidates) continue;

    for (const { word: candidate, freq } of candidates) {
      // Quick length filter
      if (Math.abs(candidate.length - lower.length) > MAX_EDIT_DISTANCE) continue;

      const dist = damerauLevenshtein(lower, candidate, MAX_EDIT_DISTANCE);
      if (dist <= MAX_EDIT_DISTANCE) {
        // Prefer closer distance, then higher frequency
        if (dist < bestDist || (dist === bestDist && freq > bestFreq)) {
          bestWord = candidate;
          bestFreq = freq;
          bestDist = dist;
        }
      }
    }
  }

  if (symspellCache.size >= MAX_CACHE_SIZE) symspellCache.clear();
  symspellCache.set(lower, bestWord);
  return bestWord;
}

/**
 * Double Metaphone phonetic fallback.
 * Encodes the misspelled word phonetically, looks up matching real words
 * in the phonetic index, and returns the highest-frequency match.
 *
 * This catches sound-alike errors that are beyond edit distance 2,
 * e.g. "nessesary" -> "necessary", "fysikal" -> "physical".
 */
export function phoneticCorrection(word: string): string | null {
  if (!initialized) return null;

  const lower = word.toLowerCase();

  // Check cache
  if (phoneticCache.has(lower)) return phoneticCache.get(lower)!;

  // If the word is in the dictionary, it's correct
  if (wordFrequency.has(lower)) {
    phoneticCache.set(lower, null);
    return null;
  }

  const [primary, alternate] = doubleMetaphone(lower);

  let bestWord: string | null = null;
  let bestFreq = -1;

  // Search both primary and alternate codes
  const codes = alternate && alternate !== primary ? [primary, alternate] : [primary];

  for (const code of codes) {
    const candidates = phoneticIndex.get(code);
    if (!candidates) continue;

    for (const { word: candidate, freq } of candidates) {
      // Skip if the candidate is the same as input
      if (candidate === lower) continue;

      // Prefer candidates with similar length (within 3 chars)
      if (Math.abs(candidate.length - lower.length) > 3) continue;

      if (freq > bestFreq) {
        bestWord = candidate;
        bestFreq = freq;
      }
    }
  }

  if (phoneticCache.size >= MAX_CACHE_SIZE) phoneticCache.clear();
  phoneticCache.set(lower, bestWord);
  return bestWord;
}
