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
} from './symspellService';

export interface LocalCorrection {
  original: string;
  correction: string;
  position: {
    start: number;
    end: number;
  };
  confidence: number;
  errorType: string;
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
 */
function applyCorrection(word: string, skipKnownWords = false): string | null {
  const match = word.match(/^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$/);
  if (!match) return null;

  const [, prefix, core, suffix] = match;

  if (skipKnownWords && isKnownWord(core)) {
    return null;
  }

  const corrected = lookupCorrection(core);
  if (!corrected) return null;

  // Preserve capitalization
  let result = corrected;
  if (core[0] === core[0].toUpperCase() && core[0] !== core[0].toLowerCase()) {
    result = corrected[0].toUpperCase() + corrected.slice(1);
  }
  if (core === core.toUpperCase() && core.length > 1) {
    result = corrected.toUpperCase();
  }

  return prefix + result + suffix;
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
 * Convert diffs between input text and model-generated text into LocalCorrection[].
 *
 * Word-level diff: for each word that differs between input and output,
 * if the words are similar enough (>0.3 similarity), treat it as a targeted
 * spelling correction. Complete rewrites (low similarity) are skipped.
 */
function diffToCorrections(inputText: string, generatedText: string): LocalCorrection[] {
  const corrections: LocalCorrection[] = [];

  const inputWords = inputText.split(/\s+/).filter(Boolean);
  const outputWords = generatedText.split(/\s+/).filter(Boolean);

  // Simple word-by-word alignment when lengths match or are close
  // For more complex diffs we could use the full LCS-based diffEngine,
  // but for spelling correction the model rarely changes word count.
  const minLen = Math.min(inputWords.length, outputWords.length);

  // Build character offset map for input words
  let charOffset = 0;
  const wordOffsets: number[] = [];
  const parts = inputText.split(/(\s+)/);
  let wordIdx = 0;
  for (const part of parts) {
    if (/^\s+$/.test(part)) {
      charOffset += part.length;
    } else {
      wordOffsets[wordIdx] = charOffset;
      charOffset += part.length;
      wordIdx++;
    }
  }

  for (let i = 0; i < minLen; i++) {
    const inputWord = inputWords[i];
    const outputWord = outputWords[i];

    if (inputWord === outputWord) continue;

    // Strip punctuation for comparison
    const inputCore = inputWord.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');
    const outputCore = outputWord.replace(/^[^a-zA-Z]+|[^a-zA-Z]+$/g, '');

    if (!inputCore || !outputCore) continue;
    if (inputCore.toLowerCase() === outputCore.toLowerCase()) continue;

    const similarity = levenshteinSimilarity(
      inputCore.toLowerCase(),
      outputCore.toLowerCase()
    );

    // Only include changes where similarity > 0.3 (skip complete rewrites)
    if (similarity <= 0.3) continue;

    // Skip if the word is in the personal dictionary
    if (personalDictionary.has(inputCore.toLowerCase())) continue;

    const start = wordOffsets[i] ?? 0;
    const end = start + inputWord.length;

    corrections.push({
      original: inputWord,
      correction: outputWord,
      position: { start, end },
      confidence: similarity, // Higher similarity = more confident it's a targeted fix
      errorType: 'spelling',
    });
  }

  return corrections;
}

/**
 * Run local correction on text using the T5 seq2seq pipeline
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
    const startTime = performance.now();

    // Run seq2seq generation
    const result = await state.pipeline('correct: ' + text, {
      max_length: 128,
    });

    const generatedText: string = result[0]?.generated_text ?? '';

    if (!generatedText) {
      return dictionaryOnlyCorrections(text);
    }

    // Diff input vs output to find corrections
    const corrections = diffToCorrections(text, generatedText);

    const elapsedMs = performance.now() - startTime;
    if (corrections.length > 0) {
      console.log(`[ONNX] Seq2Seq inference: ${elapsedMs.toFixed(1)}ms, ${corrections.length} corrections found`);
    }

    return corrections;
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

    const corrected = applyCorrection(segment, true);
    if (corrected && corrected !== segment) {
      corrections.push({
        original: segment,
        correction: corrected,
        position: { start: offset, end: offset + segment.length },
        confidence: 0.8, // Lower confidence for dictionary-only mode
        errorType: 'spelling',
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
