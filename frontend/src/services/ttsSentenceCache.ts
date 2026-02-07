/**
 * Sentence-level TTS caching utilities.
 *
 * Splits text into sentences, hashes them for cache keys,
 * and provides an in-memory LRU AudioBuffer cache.
 */

// Common abbreviations that end with a period but don't end a sentence.
const ABBREVIATIONS = new Set([
  'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
  'st', 'ave', 'blvd', 'dept', 'est', 'govt',
  'inc', 'ltd', 'corp', 'vs', 'etc', 'approx',
  'e.g', 'i.e', 'u.s', 'u.k',
]);

/**
 * Split text into sentences on `.!?` followed by whitespace,
 * handling common abbreviations. Merges fragments under 3 chars
 * with the previous sentence.
 */
export function splitIntoSentences(text: string): string[] {
  if (!text || !text.trim()) return [];

  const raw: string[] = [];
  let current = '';

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    current += ch;

    if ((ch === '.' || ch === '!' || ch === '?') && i + 1 < text.length && /\s/.test(text[i + 1])) {
      // Check if period follows an abbreviation
      if (ch === '.') {
        // Grab the word before the period
        const beforeDot = current.slice(0, -1).trimStart();
        const lastWord = beforeDot.split(/\s+/).pop()?.toLowerCase() || '';
        if (ABBREVIATIONS.has(lastWord) || ABBREVIATIONS.has(lastWord.replace(/\./g, ''))) {
          continue; // Not a sentence boundary
        }
      }
      raw.push(current.trim());
      current = '';
    }
  }

  // Remaining text
  if (current.trim()) {
    raw.push(current.trim());
  }

  // Merge tiny fragments (< 3 chars) with previous sentence
  const merged: string[] = [];
  for (const s of raw) {
    if (s.length < 3 && merged.length > 0) {
      merged[merged.length - 1] += ' ' + s;
    } else {
      merged.push(s);
    }
  }

  return merged.filter(s => s.length > 0);
}

/**
 * SHA-256 hash of `voice:text` (lowercased, trimmed) as hex string.
 */
export async function hashSentence(text: string, voice: string): Promise<string> {
  const key = `${voice}:${text.trim().toLowerCase()}`;
  const encoded = new TextEncoder().encode(key);
  const digest = await crypto.subtle.digest('SHA-256', encoded);
  return Array.from(new Uint8Array(digest))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * In-memory LRU cache for decoded AudioBuffers keyed by content hash.
 */
export class SentenceAudioCache {
  private maxSize: number;
  private cache: Map<string, AudioBuffer>;

  constructor(maxSize = 200) {
    this.maxSize = maxSize;
    this.cache = new Map();
  }

  has(hash: string): boolean {
    return this.cache.has(hash);
  }

  get(hash: string): AudioBuffer | undefined {
    const buf = this.cache.get(hash);
    if (buf) {
      // Move to end (most recently used)
      this.cache.delete(hash);
      this.cache.set(hash, buf);
    }
    return buf;
  }

  set(hash: string, buffer: AudioBuffer): void {
    if (this.cache.has(hash)) {
      this.cache.delete(hash);
    } else if (this.cache.size >= this.maxSize) {
      // Evict oldest (first key)
      const oldest = this.cache.keys().next().value!;
      this.cache.delete(oldest);
    }
    this.cache.set(hash, buffer);
  }

  clear(): void {
    this.cache.clear();
  }

  get size(): number {
    return this.cache.size;
  }
}

/** Module-level singleton */
export const sentenceAudioCache = new SentenceAudioCache();
