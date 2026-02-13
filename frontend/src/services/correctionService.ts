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
  type: 'spelling' | 'omission' | 'insertion' | 'transposition' | 'substitution'
    | 'grammar' | 'confusion' | 'phonetic' | 'homophone' | 'clarity' | 'style'
    | 'subject_verb' | 'article' | 'verb_tense' | 'function_word'
    | 'pronoun_case' | 'run_on';
  start: number;
  end: number;
  confidence: number;
  explanation?: string;
  source?: 'model' | 'regex' | 'api';
}

/**
 * Map a LocalCorrection from the ONNX model to the UI Correction format.
 */
function mapLocalCorrection(lc: LocalCorrection): Correction {
  return {
    original: lc.original,
    suggested: lc.correction,
    type: lc.errorType as Correction['type'], // propagate granular error type from onnxModel — c.secrist 2/8
    start: lc.position.start,
    end: lc.position.end,
    confidence: lc.confidence,
    source: 'model',
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
    source: 'regex',
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
 * Map an API correction to the UI Correction format.
 * Filters out corrections without valid position data.
 */
function mapApiCorrection(c: any): Correction | null {
  const start = c.position?.start;
  const end = c.position?.end;
  if (typeof start !== 'number' || typeof end !== 'number' || start === end) return null;
  return {
    original: c.original || '',
    suggested: c.correction || c.suggested || '',
    type: c.error_type || c.type || 'spelling',
    start,
    end,
    confidence: c.confidence ?? 0.9,
    explanation: c.explanation,
    source: 'api',
  };
}

/**
 * Merge corrections from multiple sources, removing overlapping ranges.
 * Priority: AI API > model (spelling + grammar) > context rules > regex grammar.
 * Model-based grammar corrections take precedence over regex-based ones.
 * When corrections overlap at the same start position, larger spans are preferred
 * since they represent more meaningful corrections.
 */
function mergeCorrections(...groups: Correction[][]): Correction[] {
  // Flatten all groups in priority order (first group = highest priority)
  const all: Correction[] = groups.flat();
  const merged: Correction[] = [];

  // Sort by start position, then prefer model over regex for same position,
  // then prefer larger spans
  all.sort((a, b) => {
    if (a.start !== b.start) return a.start - b.start;
    // Model corrections win over regex at same position
    const aIsModel = a.source === 'model' || a.source === 'api';
    const bIsModel = b.source === 'model' || b.source === 'api';
    if (aIsModel !== bIsModel) return aIsModel ? -1 : 1;
    // Larger spans preferred
    return (b.end - b.start) - (a.end - a.start);
  });

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

  // Run local checks and API call in parallel — AI always participates
  const [localCorrections, grammarResults, contextResults, apiCorrections] = await Promise.all([
    runLocalCorrection(text),
    Promise.resolve(checkGrammar(text)),
    Promise.resolve(checkContextualConfusions(text)),
    api.getCorrections(text)
      .then((res) =>
        res.data.corrections
          .map(mapApiCorrection)
          .filter((c): c is Correction => c !== null)
      )
      .catch((err) => {
        console.warn('[Corrections] API call failed:', err?.message ?? err);
        return [] as Correction[];
      }),
  ]);

  const spelling = localCorrections.map(mapLocalCorrection);
  const context = contextResults.map(mapContextCorrection);
  const grammar = grammarResults.map(mapGrammarCorrection);

  console.log(
    '[Corrections] Results — local:%d grammar:%d context:%d api:%d',
    spelling.length, grammar.length, context.length, apiCorrections.length
  );

  // Merge with priority: AI > spelling > context > grammar
  return mergeCorrections(apiCorrections, spelling, context, grammar);
}
