/**
 * ONNX Model Service - Browser-based Quick Correction
 *
 * Runs the Quick Correction Model locally in the browser using ONNX Runtime Web.
 * Provides fast corrections (<100ms) without API calls.
 *
 * The model detects error positions (BIO labels). Corrections come from a
 * three-tier fallback chain:
 * 1. Dictionary lookup — base (~34K) + user personalized error profile (fastest)
 * 2. SymSpell edit-distance — catches transpositions/omissions within distance 2
 * 3. Phonetic matching — Double Metaphone for sound-alike errors
 */

// Dynamic imports — loaded lazily to avoid crashing the app if ONNX backends
// fail to register (e.g. missing WebGL/WASM support).
// Import from 'onnxruntime-web/wasm' to only register the WASM backend,
// avoiding registerBackend crashes from WebGL/WebGPU in v1.18+.
let ort: typeof import('onnxruntime-web') | null = null;

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
  session: any | null; // ort.InferenceSession when loaded
  tokenizer: any | null;
  loading: boolean;
  error: string | null;
  baseDictionary: Record<string, string>;
  userDictionary: Record<string, string>;
}

const state: OnnxModelState = {
  session: null,
  tokenizer: null,
  loading: false,
  error: null,
  baseDictionary: {},
  userDictionary: {},
};

const MODEL_PATH = '/models/quick_correction_base_v1';

/**
 * Load the ONNX model, tokenizer, and base correction dictionary
 */
export async function loadModel(): Promise<void> {
  if (state.session && state.tokenizer) {
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
    console.log('[ONNX] Loading Quick Correction Model...');

    // Load base correction dictionary
    try {
      const dictResponse = await fetch(`${MODEL_PATH}/correction_dict.json`);
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

    // Initialize SymSpell + phonetic index (runs in parallel with ONNX load)
    // Non-blocking: if it fails, we still have dictionary-only mode
    await initSymSpell();

    // Dynamically import onnxruntime-web (avoids registerBackend crash at startup)
    if (!ort) {
      try {
        ort = await import('onnxruntime-web/wasm') as typeof import('onnxruntime-web');
      } catch (importErr) {
        console.warn('[ONNX] Failed to import onnxruntime-web:', importErr);
        state.error = 'ONNX Runtime not available — using dictionary-only mode';
        state.loading = false;
        return;
      }
    }

    // Load ONNX session
    state.session = await ort.InferenceSession.create(`${MODEL_PATH}/model.onnx`, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });

    console.log('[ONNX] Model loaded successfully');

    // Dynamically import tokenizer
    const { AutoTokenizer } = await import('@xenova/transformers');
    state.tokenizer = await AutoTokenizer.from_pretrained(MODEL_PATH + '/');

    console.log('[ONNX] Tokenizer loaded successfully');
    console.log('[ONNX] Quick Correction ready for inference');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.warn('[ONNX] Failed to load model:', errorMessage);
    state.error = errorMessage;

    // Clear partial state
    state.session = null;
    state.tokenizer = null;
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
  // User dict entries override base, so total is base + unique user entries
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

  // Skip Tier 2/3 for very short words (≤2 chars) — edit distance and
  // phonetic matching are unreliable at this length ("AI"→"A", "IT"→"I", etc.)
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
 * When called from dictionaryOnlyCorrections (no ONNX model), we skip
 * words that are known valid English words to avoid false positives.
 */
function applyCorrection(word: string, skipKnownWords = false): string | null {
  // Strip punctuation to look up the core word
  const match = word.match(/^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$/);
  if (!match) return null;

  const [, prefix, core, suffix] = match;

  // In dictionary-only mode (no ONNX model), skip words that are in the
  // frequency dictionary — they're valid English words, not errors.
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
 * Compute softmax over logits to get confidence
 */
function softmax(logits: number[]): number[] {
  const maxLogit = Math.max(...logits);
  const exps = logits.map(l => Math.exp(l - maxLogit));
  const sumExps = exps.reduce((a, b) => a + b, 0);
  return exps.map(e => e / sumExps);
}

/**
 * Decode model predictions into corrections
 */
function decodeCorrections(
  text: string,
  predictions: Float32Array,
  tokens: string[],
  offsetMapping: number[][]
): LocalCorrection[] {
  const corrections: LocalCorrection[] = [];

  // Find error tokens (label != 0)
  let currentError: {
    tokens: string[];
    offsets: number[][];
    confidences: number[];
  } | null = null;

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];

    // Skip special tokens
    if (token === '[CLS]' || token === '[SEP]' || token === '[PAD]') {
      if (currentError) {
        const correction = createCorrection(text, currentError);
        if (correction) corrections.push(correction);
        currentError = null;
      }
      continue;
    }

    // Get prediction via softmax for proper confidence
    const startIdx = i * 3; // 3 labels: O, B-ERROR, I-ERROR
    const logits = [
      predictions[startIdx],
      predictions[startIdx + 1],
      predictions[startIdx + 2],
    ];
    const probs = softmax(logits);
    const maxIdx = probs.indexOf(Math.max(...probs));
    const confidence = probs[maxIdx];

    const isBError = maxIdx === 1;
    const isIError = maxIdx === 2;

    if (isBError) {
      // B-ERROR: start new error (flush previous if any)
      if (currentError) {
        const correction = createCorrection(text, currentError);
        if (correction) corrections.push(correction);
      }
      currentError = {
        tokens: [token],
        offsets: [offsetMapping[i]],
        confidences: [confidence],
      };
    } else if (isIError && currentError) {
      // I-ERROR: continue current error
      currentError.tokens.push(token);
      currentError.offsets.push(offsetMapping[i]);
      currentError.confidences.push(confidence);
    } else {
      // O label: end current error
      if (currentError) {
        const correction = createCorrection(text, currentError);
        if (correction) corrections.push(correction);
        currentError = null;
      }
    }
  }

  // Handle error at end
  if (currentError) {
    const correction = createCorrection(text, currentError);
    if (correction) {
      corrections.push(correction);
    }
  }

  return corrections;
}

/**
 * Create correction from error tokens
 */
function createCorrection(
  text: string,
  error: {
    tokens: string[];
    offsets: number[][];
    confidences: number[];
  }
): LocalCorrection | null {
  if (error.tokens.length === 0 || error.offsets.length === 0) {
    return null;
  }

  // Get position in text
  const start = error.offsets[0][0];
  const end = error.offsets[error.offsets.length - 1][1];
  const original = text.slice(start, end);

  if (!original.trim()) return null;

  // Look up correction in dictionaries
  const corrected = applyCorrection(original);

  if (!corrected || corrected === original) {
    // No correction found in dictionary — still report the error position
    // but without a suggestion (UI can show "possible error" indicator)
    return null;
  }

  // Average confidence
  const avgConfidence = error.confidences.reduce((a, b) => a + b, 0) / error.confidences.length;

  return {
    original,
    correction: corrected,
    position: { start, end },
    confidence: avgConfidence,
    errorType: 'spelling',
  };
}

/**
 * Run local correction on text
 */
export async function runLocalCorrection(text: string): Promise<LocalCorrection[]> {
  // Ensure model is loaded
  if (!state.session || !state.tokenizer) {
    await loadModel();
  }

  // Check if model loaded successfully
  if (!state.session || !state.tokenizer) {
    // Fallback: dictionary-only mode when model isn't available
    return dictionaryOnlyCorrections(text);
  }

  try {
    const startTime = performance.now();

    // Tokenize
    const encoded = await state.tokenizer(text, {
      padding: true,
      truncation: true,
      max_length: 128,
      return_tensors: 'onnx',
      return_offsets_mapping: true,
    });

    // Convert to ONNX tensors
    const ortModule = ort;
    if (!ortModule) {
      return dictionaryOnlyCorrections(text);
    }
    const inputIds = new ortModule.Tensor('int64', encoded.input_ids.data, encoded.input_ids.dims);
    const attentionMask = new ortModule.Tensor('int64', encoded.attention_mask.data, encoded.attention_mask.dims);

    // Run inference
    const outputs = await state.session.run({
      input_ids: inputIds,
      attention_mask: attentionMask,
    });

    // Get predictions
    const logits = outputs.logits;
    const predictions = logits.data as Float32Array;

    // Get tokens
    const tokens = encoded.input_ids.data.map((id: number) =>
      state.tokenizer!.decode([id], { skip_special_tokens: false })
    );

    // Decode corrections
    const corrections = decodeCorrections(text, predictions, tokens, encoded.offset_mapping);

    const elapsedMs = performance.now() - startTime;
    if (corrections.length > 0) {
      console.log(`[ONNX] Inference: ${elapsedMs.toFixed(1)}ms, ${corrections.length} corrections found`);
    }

    return corrections;
  } catch (error) {
    console.error('[ONNX] Inference failed:', error);
    // Fallback to dictionary-only mode
    return dictionaryOnlyCorrections(text);
  }
}

/**
 * Dictionary-only correction mode (fallback when ONNX model isn't available).
 * Checks every word against the three-tier correction chain.
 * Uses skipKnownWords=true to prevent false positives on valid English words
 * (since without the ONNX model we don't have error-position detection).
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
  return state.session !== null && state.tokenizer !== null;
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
