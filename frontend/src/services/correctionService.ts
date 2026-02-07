import { api } from './api';
import { runLocalCorrection, isInPersonalDictionary } from './onnxModel';
import type { LocalCorrection } from './onnxModel';
import { checkGrammar } from './grammarRules';
import type { GrammarCorrection } from './grammarRules';
import { checkContextualConfusions } from './contextRules';
import type { ContextCorrection } from './contextRules';

export interface Correction {
  original: string;
  suggested: string;
  type: 'spelling' | 'grammar' | 'confusion' | 'phonetic' | 'homophone' | 'clarity' | 'style';
  start: number;
  end: number;
  confidence: number;
  explanation?: string;
}

/**
 * Map a LocalCorrection from the ONNX model to the UI Correction format.
 */
function mapLocalCorrection(lc: LocalCorrection): Correction {
  return {
    original: lc.original,
    suggested: lc.correction,
    type: 'spelling',
    start: lc.position.start,
    end: lc.position.end,
    confidence: lc.confidence,
  };
}

function mapGrammarCorrection(gc: GrammarCorrection): Correction {
  return {
    original: gc.original,
    suggested: gc.suggested,
    type: 'grammar',
    start: gc.start,
    end: gc.end,
    confidence: gc.confidence,
    explanation: gc.explanation,
  };
}

function mapContextCorrection(cc: ContextCorrection): Correction {
  return {
    original: cc.original,
    suggested: cc.suggested,
    type: 'confusion',
    start: cc.start,
    end: cc.end,
    confidence: cc.confidence,
    explanation: cc.explanation,
  };
}

/**
 * Merge corrections from multiple sources, removing overlapping ranges.
 * Priority: spelling > context > grammar (earlier in the array wins).
 * When corrections overlap at the same start position, larger spans are preferred
 * since they represent more meaningful corrections.
 */
function mergeCorrections(...groups: Correction[][]): Correction[] {
  // Flatten all groups in priority order (first group = highest priority)
  const all: Correction[] = groups.flat();
  const merged: Correction[] = [];

  // Sort by start position, then prefer larger spans for same start
  all.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));

  for (const correction of all) {
    // Skip words the user added to their personal dictionary
    if (isInPersonalDictionary(correction.original)) continue;

    // Skip if this correction overlaps with any already-accepted correction
    const overlaps = merged.some(
      (existing) => correction.start < existing.end && correction.end > existing.start
    );
    if (!overlaps) {
      merged.push(correction);
    }
  }

  return merged;
}

export async function getCorrections(text: string): Promise<Correction[]> {
  if (!text.trim()) return [];

  // Run all local checks in parallel
  const [localCorrections, grammarResults, contextResults] = await Promise.all([
    runLocalCorrection(text),
    Promise.resolve(checkGrammar(text)),
    Promise.resolve(checkContextualConfusions(text)),
  ]);

  const spelling = localCorrections.map(mapLocalCorrection);
  const context = contextResults.map(mapContextCorrection);
  const grammar = grammarResults.map(mapGrammarCorrection);

  // Merge with priority: spelling > context > grammar
  const merged = mergeCorrections(spelling, context, grammar);

  if (merged.length > 0) {
    return merged;
  }

  // Fall back to cloud API for deeper analysis only if local checks found nothing
  try {
    const response = await api.getCorrections(text);
    return response.data.corrections.map((c: any) => ({
      original: c.original || '',
      suggested: c.correction || c.suggested || '',
      type: c.error_type || c.type || 'spelling',
      start: c.position?.start ?? 0,
      end: c.position?.end ?? 0,
      confidence: c.confidence ?? 0.9,
      explanation: c.explanation,
    })) as Correction[];
  } catch {
    return [];
  }
}
