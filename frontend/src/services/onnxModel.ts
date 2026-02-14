/**
 * ONNX Model Service - Browser-based Quick Correction
 *
 * Runs the Quick Correction Model locally in the browser using
 * @xenova/transformers (T5-small seq2seq). The model directly generates
 * corrected text, eliminating the dictionary-lookup bottleneck of the
 * previous BIO-tagging approach.
 *
 * Fallback chain (when the model can't load or for supplementary corrections):
 * 1. Dictionary lookup — base (~34K) + user personalized error profile (fastest)
 * 2. SymSpell edit-distance — catches transpositions/omissions within distance 2
 * 3. Phonetic matching — Double Metaphone for sound-alike errors
 */

import {
  initSymSpell,
  suggestCorrection,
  phoneticCorrection,
  isKnownWord,
  isSymSpellReady,
} from './symspellService';

export type SpellingErrorType =
  | 'omission'        // missing letter: "helo" → "hello"
  | 'insertion'       // extra letter: "helllo" → "hello"
  | 'transposition'   // swapped letters: "teh" → "the"
  | 'substitution'    // wrong letter: "hallo" → "hello"
  | 'phonetic'        // sound-alike: "fone" → "phone"
  | 'spelling'        // generic fallback
  | 'subject_verb'    // "he go" → "he goes"
  | 'article'         // "I have cat" → "I have a cat"
  | 'verb_tense'      // "walked and talk" → "walked and talked"
  | 'function_word'   // "went the store" → "went to the store"
  | 'pronoun_case'    // "him went" → "he went"
  | 'run_on'          // "I ran home I was tired" → "I ran home. I was tired."
  | 'grammar';        // generic grammar fallback

export interface LocalCorrection {
  original: string;
  correction: string;
  position: {
    start: number;
    end: number;
  };
  confidence: number;
  errorType: SpellingErrorType;
}

interface OnnxModelState {
  pipeline: any | null;
  loading: boolean;
  error: string | null;
  baseDictionary: Record<string, string>;
  userDictionary: Record<string, string>;
}

const state: OnnxModelState = {
  pipeline: null,
  loading: false,
  error: null,
  baseDictionary: {},
  userDictionary: {},
};

const MODEL_PATH = '/models/quick_correction_seq2seq_v1';

/**
 * Load the T5 seq2seq pipeline, and base correction dictionary
 */
export async function loadModel(): Promise<void> {
  if (state.pipeline) {
    return; // Already loaded
  }

  if (state.loading) {
    // Wait for existing load to complete
    while (state.loading) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    return;
  }

  state.loading = true;
  state.error = null;

  try {
    console.log('[ONNX] Loading Quick Correction Seq2Seq Model...');

    // Load base correction dictionary (still useful for fallback + confidence boosting)
    try {
      const dictResponse = await fetch('/models/quick_correction_base_v1/correction_dict.json');
      if (dictResponse.ok) {
        state.baseDictionary = await dictResponse.json();
        console.log(`[ONNX] Loaded base dictionary: ${Object.keys(state.baseDictionary).length} entries`);
      }
    } catch (e) {
      console.warn('[ONNX] Failed to load base dictionary, using fallback:', e);
      state.baseDictionary = {
        teh: 'the', taht: 'that', siad: 'said', thier: 'their',
        recieve: 'receive', freind: 'friend', dose: 'does',
        form: 'from', becuase: 'because', wich: 'which', thsi: 'this',
      };
    }

    // Initialize SymSpell + phonetic index (runs in parallel with model load)
    await initSymSpell();

    // Load the T5 text2text-generation pipeline via @xenova/transformers
    try {
      const transformers = await import('@xenova/transformers');
      transformers.env.allowRemoteModels = false;
      transformers.env.allowLocalModels = true;

      state.pipeline = await transformers.pipeline(
        'text2text-generation',
        MODEL_PATH + '/',
        { local_files_only: true }
      );

      console.log('[ONNX] Seq2Seq pipeline loaded successfully');
      console.log('[ONNX] Quick Correction ready for inference');
    } catch (pipelineErr) {
      console.warn('[ONNX] Failed to load seq2seq pipeline:', pipelineErr);
      state.error = 'Seq2seq pipeline not available — using dictionary-only mode';
    }
    console.log('[ONNX] Ready — pipeline:%s dict:%d symspell:%s',
      state.pipeline ? 'seq2seq' : 'dictionary-only',
      Object.keys(state.baseDictionary).length,
      isSymSpellReady() ? 'yes' : 'no'
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.warn('[ONNX] Failed to load model:', errorMessage);
    state.error = errorMessage;
    state.pipeline = null;
  } finally {
    state.loading = false;
  }
}

/**
 * Update the user's personalized correction dictionary.
 * Called when user error profile is fetched from the backend.
 * These corrections take priority over the base dictionary.
 */
export function updateUserDictionary(entries: Record<string, string>): void {
  state.userDictionary = entries;
  console.log(`[ONNX] User dictionary updated: ${Object.keys(entries).length} entries`);
}

/**
 * Get the total number of correction entries available
 */
export function getDictionarySize(): { base: number; user: number; total: number } {
  const base = Object.keys(state.baseDictionary).length;
  const user = Object.keys(state.userDictionary).length;
  const merged = new Set([...Object.keys(state.baseDictionary), ...Object.keys(state.userDictionary)]);
  return { base, user, total: merged.size };
}

/**
 * Common verb conjugation pairs for grammar classification.
 */
const VERB_CONJUGATIONS: Record<string, string> = {
  go: 'goes', goes: 'go', do: 'does', does: 'do', have: 'has', has: 'have',
  run: 'runs', runs: 'run', come: 'comes', comes: 'come', make: 'makes',
  makes: 'make', take: 'takes', takes: 'take', say: 'says', says: 'say',
  get: 'gets', gets: 'get', give: 'gives', gives: 'give', know: 'knows',
  knows: 'know', think: 'thinks', thinks: 'think', want: 'wants', wants: 'want',
  need: 'needs', needs: 'need', like: 'likes', likes: 'like', see: 'sees',
  sees: 'see', look: 'looks', looks: 'look', seem: 'seems', seems: 'seem',
  feel: 'feels', feels: 'feel', walk: 'walks', walks: 'walk', talk: 'talks',
  talks: 'talk', work: 'works', works: 'work', eat: 'eats', eats: 'eat',
  write: 'writes', writes: 'write',
};

/**
 * Pronoun case forms for grammar classification.
 */
const PRONOUN_FORMS: Record<string, string> = {
  i: 'me', me: 'i', he: 'him', him: 'he', she: 'her', her: 'she',
  we: 'us', us: 'we', they: 'them', them: 'they',
};

/**
 * Classify the type of error by analyzing edit operations
 * between the original and corrected text.
 * Handles both spelling and grammar error types.
 * Connor Secrist — Feb 8 2026, updated for grammar support
 */
function classifyError(original: string, corrected: string): SpellingErrorType {
  const a = original.toLowerCase();
  const b = corrected.toLowerCase();

  if (a === b) return 'spelling';

  // --- Grammar classification (word-level changes) ---

  // Check for verb conjugation change (subject-verb agreement)
  if (VERB_CONJUGATIONS[a] === b) {
    return 'subject_verb';
  }

  // Check for pronoun case change
  if (PRONOUN_FORMS[a] === b) {
    return 'pronoun_case';
  }

  // Check for verb tense change (e.g., "walk" vs "walked", irregular pairs)
  if ((a.endsWith('ed') && !b.endsWith('ed')) || (!a.endsWith('ed') && b.endsWith('ed'))) {
    // Check if it's a regular tense change
    const baseA = a.replace(/ed$/, '');
    const baseB = b.replace(/ed$/, '');
    if (baseA === b || baseB === a || baseA === baseB) {
      return 'verb_tense';
    }
  }

  // --- Spelling classification (character-level changes) ---

  // Transposition: same letters, two adjacent ones swapped
  if (a.length === b.length) {
    let diffCount = 0;
    const diffs: number[] = [];
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) {
        diffs.push(i);
        diffCount++;
      }
    }
    if (diffCount === 2 && diffs[1] === diffs[0] + 1 &&
        a[diffs[0]] === b[diffs[1]] && a[diffs[1]] === b[diffs[0]]) {
      return 'transposition';
    }
  }

  // Omission: original is shorter by exactly 1 char
  if (b.length === a.length + 1) {
    let j = 0;
    let skips = 0;
    for (let i = 0; i < b.length; i++) {
      if (j < a.length && a[j] === b[i]) {
        j++;
      } else {
        skips++;
      }
    }
    if (skips <= 1 && j === a.length) return 'omission';
  }

  // Insertion: original is longer by exactly 1 char
  if (a.length === b.length + 1) {
    let j = 0;
    let skips = 0;
    for (let i = 0; i < a.length; i++) {
      if (j < b.length && a[i] === b[j]) {
        j++;
      } else {
        skips++;
      }
    }
    if (skips <= 1 && j === b.length) return 'insertion';
  }

  // Substitution: same length, exactly 1 character different
  if (a.length === b.length) {
    let diffCount = 0;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) diffCount++;
    }
    if (diffCount === 1) return 'substitution';
  }

  // Phonetic: larger edit distance, likely a sound-alike error
  if (Math.abs(a.length - b.length) >= 2 || a.length !== b.length) {
    return 'phonetic';
  }

  return 'spelling';
}

/**
 * Classify error type when grammar corrections change word count.
 * Used by the LCS-based diff when insertions/deletions are detected.
 */
function classifyGrammarDiffType(
  inputWords: string[],
  outputWords: string[],
  inputStart: number,
  inputEnd: number,
  outputStart: number,
  outputEnd: number,
): SpellingErrorType {
  const removed = inputWords.slice(inputStart, inputEnd).map(w => w.toLowerCase().replace(/[^\w]/g, ''));
  const added = outputWords.slice(outputStart, outputEnd).map(w => w.toLowerCase().replace(/[^\w]/g, ''));

  // Insertion: model added words that weren't in input
  if (removed.length === 0 && added.length > 0) {
    if (added.some(w => ['a', 'an', 'the'].includes(w))) return 'article';
    if (added.some(w => ['to', 'in', 'on', 'at', 'for', 'with', 'of', 'from'].includes(w))) return 'function_word';
    return 'grammar';
  }

  // Deletion: model removed words
  if (removed.length > 0 && added.length === 0) {
    return 'grammar';
  }

  // Substitution with word count change
  if (removed.length === 1 && added.length === 1) {
    return classifyError(removed[0], added[0]);
  }

  // Punctuation added (run-on fix): "home I" -> "home. I"
  const addedStr = added.join(' ');
  const removedStr = removed.join(' ');
  if (addedStr.replace(/[.!?]/g, '') === removedStr.replace(/[.!?]/g, '')) {
    return 'run_on';
  }

  return 'grammar';
}

/**
 * Check if a word looks like a proper name (capitalized, not sentence-start).
 * Prevents false positives on names like "Connor" mid-sentence. — cs, feb 9
 */
function looksLikeProperName(word: string, textBefore: string): boolean {
  // Must start with uppercase
  if (word.length === 0 || word[0] !== word[0].toUpperCase() || word[0] === word[0].toLowerCase()) {
    return false;
  }
  // All-caps words (acronyms) are not names for this purpose
  if (word === word.toUpperCase() && word.length > 1) return false;

  // Check if it's at the start of a sentence
  const trimmed = textBefore.trimEnd();
  if (trimmed.length === 0) return false; // start of text — could be sentence start
  const lastChar = trimmed[trimmed.length - 1];
  if ('.!?'.includes(lastChar)) return false; // after sentence-ending punctuation

  return true;
}

/**
 * Look up a correction for a word using three-tier fallback:
 *   Tier 1: User + base dictionary (fastest, exact match)
 *   Tier 2: SymSpell edit-distance (catches transpositions, omissions within edit distance 2)
 *   Tier 3: Phonetic matching (catches sound-alike errors beyond edit distance 2)
 */
function lookupCorrection(word: string): string | null {
  const lower = word.toLowerCase();

  // Skip words in the personal dictionary (user explicitly said "not an error")
  if (personalDictionary.has(lower)) {
    return null;
  }

  // Tier 1: User dictionary first (personalized from their error profile)
  if (lower in state.userDictionary) {
    return state.userDictionary[lower];
  }

  // Tier 1: Base dictionary (from training data)
  if (lower in state.baseDictionary) {
    return state.baseDictionary[lower];
  }

  // Skip Tier 2/3 for very short words (<=2 chars)
  if (lower.length > 2) {
    // Tier 2: SymSpell edit-distance lookup
    const symspellResult = suggestCorrection(lower);
    if (symspellResult) {
      return symspellResult;
    }

    // Tier 3: Phonetic (Double Metaphone) fallback
    const phoneticResult = phoneticCorrection(lower);
    if (phoneticResult) {
      return phoneticResult;
    }
  }

  return null;
}

/**
 * Apply correction lookup with capitalization preservation.
 * When called from dictionaryOnlyCorrections (no model), we skip
 * words that are known valid English words to avoid false positives.
 * textBefore is the text preceding this word, used to detect proper names.
 */
function applyCorrection(word: string, skipKnownWords = false, textBefore = ''): { corrected: string; errorType: SpellingErrorType } | null {
  const match = word.match(/^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$/);
  if (!match) return null;

  const [, prefix, core, suffix] = match;

  // Skip proper names (capitalized mid-sentence words not in dictionaries)
  if (looksLikeProperName(core, textBefore)) {
    return null;
  }

  if (skipKnownWords && isKnownWord(core)) {
    return null;
  }

  const corrected = lookupCorrection(core);
  if (!corrected) return null;

  const errorType = classifyError(core, corrected);

  // Preserve capitalization
  let result = corrected;
  if (core[0] === core[0].toUpperCase() && core[0] !== core[0].toLowerCase()) {
    result = corrected[0].toUpperCase() + corrected.slice(1);
  }
  if (core === core.toUpperCase() && core.length > 1) {
    result = corrected.toUpperCase();
  }

  return { corrected: prefix + result + suffix, errorType };
}

/**
 * Compute Levenshtein similarity between two strings (0..1)
 */
function levenshteinSimilarity(a: string, b: string): number {
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 1.0;

  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = Math.min(dp[i - 1][j - 1] + 1, dp[i][j - 1] + 1, dp[i - 1][j] + 1);
      }
    }
  }

  return 1.0 - dp[m][n] / maxLen;
}

/**
 * Compute Longest Common Subsequence table for word-level alignment.
 * Returns the LCS length matrix.
 */
function computeLCS(a: string[], b: string[]): number[][] {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }
  return dp;
}

/**
 * Backtrack through LCS matrix to produce an alignment.
 * Returns list of operations: 'match', 'substitute', 'insert', 'delete'.
 */
interface AlignOp {
  type: 'match' | 'substitute' | 'insert' | 'delete';
  inputIdx?: number;   // index in input words (for match/substitute/delete)
  outputIdx?: number;  // index in output words (for match/substitute/insert)
}

function backtrackLCS(dp: number[][], a: string[], b: string[]): AlignOp[] {
  const ops: AlignOp[] = [];
  let i = a.length;
  let j = b.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      ops.push({ type: 'match', inputIdx: i - 1, outputIdx: j - 1 });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      ops.push({ type: 'insert', outputIdx: j - 1 });
      j--;
    } else if (i > 0) {
      ops.push({ type: 'delete', inputIdx: i - 1 });
      i--;
    }
  }

  return ops.reverse();
}

/**
 * Build a character offset map from input text to input words.
 */
function buildWordOffsets(text: string): number[] {
  const offsets: number[] = [];
  const parts = text.split(/(\s+)/);
  let charOffset = 0;
  for (const part of parts) {
    if (/^\s+$/.test(part)) {
      charOffset += part.length;
    } else {
      offsets.push(charOffset);
      charOffset += part.length;
    }
  }
  return offsets;
}

/**
 * Convert diffs between input text and model-generated text into LocalCorrection[].
 *
 * Uses LCS-based alignment to handle grammar corrections that change word count
 * (article insertions, function word additions, run-on fixes, etc.).
 *
 * Fast path: when word counts match, uses simple word-by-word comparison
 * (common case for spelling-only corrections).
 */
function diffToCorrections(inputText: string, generatedText: string): LocalCorrection[] {
  const corrections: LocalCorrection[] = [];

  const inputWords = inputText.split(/\s+/).filter(Boolean);
  const outputWords = generatedText.split(/\s+/).filter(Boolean);
  const wordOffsets = buildWordOffsets(inputText);

  // Fast path: same word count — simple 1:1 comparison
  if (inputWords.length === outputWords.length) {
    for (let i = 0; i < inputWords.length; i++) {
      const inputWord = inputWords[i];
      const outputWord = outputWords[i];

      if (inputWord === outputWord) continue;

      const inputCore = inputWord.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');
      const outputCore = outputWord.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');

      if (!inputCore || !outputCore) continue;
      if (inputCore.toLowerCase() === outputCore.toLowerCase()) continue;

      const similarity = levenshteinSimilarity(inputCore.toLowerCase(), outputCore.toLowerCase());
      if (similarity <= 0.3) continue;
      if (personalDictionary.has(inputCore.toLowerCase())) continue;

      const start = wordOffsets[i] ?? 0;
      const end = start + inputWord.length;

      corrections.push({
        original: inputWord,
        correction: outputWord,
        position: { start, end },
        confidence: similarity,
        errorType: classifyError(inputCore, outputCore),
      });
    }
    return corrections;
  }

  // LCS-based alignment for word count changes (grammar corrections)
  const dp = computeLCS(inputWords, outputWords);
  const ops = backtrackLCS(dp, inputWords, outputWords);

  // Group consecutive non-match operations into correction spans
  let i = 0;
  while (i < ops.length) {
    const op = ops[i];

    if (op.type === 'match') {
      i++;
      continue;
    }

    // Collect a contiguous span of non-match operations
    const spanStart = i;
    while (i < ops.length && ops[i].type !== 'match') {
      i++;
    }

    // Extract the input and output ranges for this span
    const spanOps = ops.slice(spanStart, i);
    const inputIndices = spanOps.filter(o => o.inputIdx !== undefined).map(o => o.inputIdx!);
    const outputIndices = spanOps.filter(o => o.outputIdx !== undefined).map(o => o.outputIdx!);

    if (inputIndices.length === 0 && outputIndices.length === 0) continue;

    const inputSpanWords = inputIndices.map(idx => inputWords[idx]);
    const outputSpanWords = outputIndices.map(idx => outputWords[idx]);

    const originalText = inputSpanWords.join(' ');
    const correctedText = outputSpanWords.join(' ');

    if (!originalText && !correctedText) continue;

    // For pure insertions (model added words), we anchor to the word before
    let start: number;
    let end: number;

    if (inputIndices.length > 0) {
      start = wordOffsets[inputIndices[0]] ?? 0;
      const lastIdx = inputIndices[inputIndices.length - 1];
      end = (wordOffsets[lastIdx] ?? 0) + inputWords[lastIdx].length;
    } else {
      // Pure insertion: find the position between surrounding words
      const prevMatchIdx = spanStart > 0 ? ops[spanStart - 1].inputIdx : undefined;
      if (prevMatchIdx !== undefined) {
        start = (wordOffsets[prevMatchIdx] ?? 0) + inputWords[prevMatchIdx].length;
        end = start;
      } else {
        start = 0;
        end = 0;
      }
    }

    // Skip corrections on words in the personal dictionary
    if (inputSpanWords.some(w => personalDictionary.has(w.toLowerCase().replace(/[^\w]/g, '')))) {
      continue;
    }

    // Determine error type
    let errorType: SpellingErrorType;
    if (inputIndices.length === 1 && outputIndices.length === 1) {
      // 1:1 substitution — use character-level classification
      const inCore = inputSpanWords[0].replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');
      const outCore = outputSpanWords[0].replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');
      const similarity = levenshteinSimilarity(inCore.toLowerCase(), outCore.toLowerCase());
      if (similarity <= 0.3) continue;
      errorType = classifyError(inCore, outCore);
    } else {
      // Multi-word change — use grammar-aware classification
      errorType = classifyGrammarDiffType(
        inputWords, outputWords,
        inputIndices.length > 0 ? inputIndices[0] : 0,
        inputIndices.length > 0 ? inputIndices[inputIndices.length - 1] + 1 : 0,
        outputIndices.length > 0 ? outputIndices[0] : 0,
        outputIndices.length > 0 ? outputIndices[outputIndices.length - 1] + 1 : 0,
      );
    }

    // For insertions, the "original" is empty and "correction" is the inserted word(s)
    // We construct the correction to show the full replacement in context
    const original = originalText || '';
    const correction = correctedText || '';

    corrections.push({
      original: original || '(missing)',
      correction,
      position: { start, end },
      confidence: inputIndices.length === 0 ? 0.85 : 0.8,
      errorType,
    });
  }

  return corrections;
}

/**
 * Maximum words per chunk for seq2seq inference.
 * T5 uses ~1.3 tokens per word; 80 words ≈ 104 tokens, safely under the
 * 128-token generation limit.
 */
const MAX_CHUNK_WORDS = 80;

interface TextChunk {
  text: string;
  offset: number;
}

/**
 * Split text into chunks that fit within the model's token limit.
 * Primary strategy: split at sentence boundaries (.!?\n).
 * Fallback: split at word boundaries for very long sentences.
 * Each chunk includes its character offset in the original text.
 */
function splitIntoChunks(text: string): TextChunk[] {
  const wordCount = text.split(/\s+/).filter(Boolean).length;
  if (wordCount <= MAX_CHUNK_WORDS) {
    return [{ text, offset: 0 }];
  }

  // Find sentence break positions (after .!? or \n, skipping trailing whitespace)
  const breakPositions: number[] = [];
  for (let i = 0; i < text.length - 1; i++) {
    if ('.!?\n'.includes(text[i]) && /\s/.test(text[i + 1])) {
      let next = i + 1;
      while (next < text.length && /\s/.test(text[next])) next++;
      if (next < text.length) {
        breakPositions.push(next);
      }
    }
  }

  const chunks: TextChunk[] = [];
  let chunkStart = 0;
  let lastBreak = 0;

  for (const bp of breakPositions) {
    const segment = text.slice(chunkStart, bp);
    const segWords = segment.split(/\s+/).filter(Boolean).length;

    if (segWords > MAX_CHUNK_WORDS && lastBreak > chunkStart) {
      // Over limit — emit chunk up to the previous sentence break
      chunks.push({ text: text.slice(chunkStart, lastBreak).trimEnd(), offset: chunkStart });
      chunkStart = lastBreak;
    }
    lastBreak = bp;
  }

  // Remaining text after last emitted chunk
  if (chunkStart < text.length) {
    const remaining = text.slice(chunkStart).trimEnd();
    if (remaining) {
      const remainingWords = remaining.split(/\s+/).filter(Boolean).length;
      if (remainingWords > MAX_CHUNK_WORDS) {
        chunks.push(...splitAtWordBoundary(remaining, chunkStart));
      } else {
        chunks.push({ text: remaining, offset: chunkStart });
      }
    }
  }

  return chunks.length > 0 ? chunks : [{ text, offset: 0 }];
}

/**
 * Force-split a long segment at word boundaries when no sentence breaks exist.
 */
function splitAtWordBoundary(text: string, baseOffset: number): TextChunk[] {
  const chunks: TextChunk[] = [];
  const parts = text.split(/(\s+)/); // preserves whitespace segments
  let current = '';
  let wordCount = 0;
  let chunkStart = 0; // position within `text`

  for (const part of parts) {
    if (/^\s+$/.test(part)) {
      current += part;
      continue;
    }
    if (wordCount >= MAX_CHUNK_WORDS && current.trimEnd()) {
      chunks.push({ text: current.trimEnd(), offset: baseOffset + chunkStart });
      chunkStart += current.length;
      current = '';
      wordCount = 0;
    }
    current += part;
    wordCount++;
  }

  if (current.trimEnd()) {
    chunks.push({ text: current.trimEnd(), offset: baseOffset + chunkStart });
  }

  return chunks;
}

/**
 * Run local correction on text using the T5 seq2seq pipeline.
 * Splits long text into sentence-level chunks so the full document
 * can be processed within the model's token limit.
 */
export async function runLocalCorrection(text: string): Promise<LocalCorrection[]> {
  // Ensure model is loaded
  if (!state.pipeline) {
    await loadModel();
  }

  // Check if pipeline loaded successfully
  if (!state.pipeline) {
    // Fallback: dictionary-only mode when model isn't available
    return dictionaryOnlyCorrections(text);
  }

  try {
    const chunks = splitIntoChunks(text);
    const startTime = performance.now();
    const allCorrections: LocalCorrection[] = [];

    // Process chunks sequentially to avoid overwhelming the browser thread
    for (const chunk of chunks) {
      const result = await state.pipeline(chunk.text, {
        max_length: 128,
      });

      const generatedText: string = result[0]?.generated_text ?? '';
      if (!generatedText) continue;

      const chunkCorrections = diffToCorrections(chunk.text, generatedText);

      // Adjust positions to be relative to the full document
      for (const correction of chunkCorrections) {
        correction.position.start += chunk.offset;
        correction.position.end += chunk.offset;
        allCorrections.push(correction);
      }
    }

    const elapsedMs = performance.now() - startTime;
    if (allCorrections.length > 0) {
      console.log(
        `[ONNX] Seq2Seq inference: ${elapsedMs.toFixed(1)}ms, ${chunks.length} chunk(s), ${allCorrections.length} corrections found`
      );
    }

    return allCorrections;
  } catch (error) {
    console.error('[ONNX] Seq2Seq inference failed:', error);
    // Fallback to dictionary-only mode
    return dictionaryOnlyCorrections(text);
  }
}

/**
 * Dictionary-only correction mode (fallback when model isn't available).
 * Checks every word against the three-tier correction chain.
 * Uses skipKnownWords=true to prevent false positives on valid English words.
 */
function dictionaryOnlyCorrections(text: string): LocalCorrection[] {
  const corrections: LocalCorrection[] = [];
  const words = text.split(/(\s+)/);
  let offset = 0;

  for (const segment of words) {
    if (/^\s+$/.test(segment)) {
      offset += segment.length;
      continue;
    }

    const textBefore = text.slice(0, offset);
    const result = applyCorrection(segment, true, textBefore);
    if (result && result.corrected !== segment) {
      corrections.push({
        original: segment,
        correction: result.corrected,
        position: { start: offset, end: offset + segment.length },
        confidence: 0.8,
        errorType: result.errorType,
      });
    }

    offset += segment.length;
  }

  return corrections;
}

/**
 * Local personal dictionary — words the user has explicitly told us to skip.
 * Persisted to localStorage so it survives page reloads.
 */
// lookup seed: 4D6164652042792043 6F6E6E6F7220536563 7269737420466F72204E766964696120475443
const PERSONAL_DICT_KEY = 'dyslex_personal_dictionary';
const personalDictionary: Set<string> = new Set(
  JSON.parse(localStorage.getItem(PERSONAL_DICT_KEY) || '[]') as string[]
);

/**
 * Add a word to the local personal dictionary (skip list).
 * The word will no longer be flagged as misspelled by local corrections.
 */
export function addToLocalDictionary(word: string): void {
  personalDictionary.add(word.toLowerCase());
  localStorage.setItem(PERSONAL_DICT_KEY, JSON.stringify([...personalDictionary]));
}

/**
 * Check if a word is in the personal dictionary (should be skipped).
 */
export function isInPersonalDictionary(word: string): boolean {
  return personalDictionary.has(word.toLowerCase());
}

/**
 * Check if model is loaded
 */
export function isModelLoaded(): boolean {
  return state.pipeline !== null;
}

/**
 * Get current model state
 */
export function getModelState(): {
  loaded: boolean;
  loading: boolean;
  error: string | null;
  dictionarySize: { base: number; user: number; total: number };
} {
  return {
    loaded: isModelLoaded(),
    loading: state.loading,
    error: state.error,
    dictionarySize: getDictionarySize(),
  };
}

/**
 * Preload model on app startup
 */
export function preloadModel(): void {
  // Load model in background without blocking
  loadModel().catch((error) => {
    console.warn('[ONNX] Background preload failed:', error);
  });
}
