import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/services/onnxModel', () => ({
  runLocalCorrection: vi.fn(),
  isInPersonalDictionary: vi.fn(),
}));

vi.mock('@/services/grammarRules', () => ({
  checkGrammar: vi.fn(),
}));

vi.mock('@/services/contextRules', () => ({
  checkContextualConfusions: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  api: {
    getCorrections: vi.fn(),
  },
}));

import { getCorrections } from '@/services/correctionService';
import { runLocalCorrection, isInPersonalDictionary } from '@/services/onnxModel';
import { checkGrammar } from '@/services/grammarRules';
import { checkContextualConfusions } from '@/services/contextRules';
import { api } from '@/services/api';

const mockRunLocal = vi.mocked(runLocalCorrection);
const mockIsPersonal = vi.mocked(isInPersonalDictionary);
const mockCheckGrammar = vi.mocked(checkGrammar);
const mockCheckContext = vi.mocked(checkContextualConfusions);
const mockApiCorrections = vi.mocked(api.getCorrections);

describe('getCorrections', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRunLocal.mockResolvedValue([]);
    mockCheckGrammar.mockReturnValue([]);
    mockCheckContext.mockReturnValue([]);
    mockIsPersonal.mockReturnValue(false);
  });

  // ── Empty / whitespace ──────────────────────────────────────────────
  it('returns [] for empty string', async () => {
    const result = await getCorrections('');
    expect(result).toEqual([]);
  });

  it('returns [] for whitespace-only string', async () => {
    const result = await getCorrections('  ');
    expect(result).toEqual([]);
  });

  // ── Spelling corrections from ONNX model ──────────────────────────
  it('returns mapped spelling corrections from ONNX model', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);

    const result = await getCorrections('teh cat');
    expect(result.length).toBeGreaterThanOrEqual(1);
    const spelling = result.find((c) => c.original === 'teh');
    expect(spelling).toBeDefined();
    expect(spelling!.type).toBe('spelling');
    expect(spelling!.suggested).toBe('the');
    expect(spelling!.start).toBe(0);
    expect(spelling!.end).toBe(3);
    expect(spelling!.confidence).toBe(0.9);
  });

  // ── Grammar corrections ────────────────────────────────────────────
  it('returns mapped grammar corrections', async () => {
    mockCheckGrammar.mockReturnValue([
      {
        original: 'the the',
        suggested: 'the',
        type: 'grammar',
        start: 0,
        end: 7,
        confidence: 0.9,
        explanation: 'Doubled word.',
      },
    ]);

    const result = await getCorrections('the the cat');
    const grammar = result.find((c) => c.original === 'the the');
    expect(grammar).toBeDefined();
    expect(grammar!.type).toBe('grammar');
    expect(grammar!.suggested).toBe('the');
  });

  // ── Context corrections ────────────────────────────────────────────
  it('returns mapped context corrections', async () => {
    mockCheckContext.mockReturnValue([
      {
        original: 'there',
        suggested: 'their',
        type: 'confusion',
        start: 0,
        end: 5,
        confidence: 0.75,
        explanation: 'Use "their" to show possession.',
      },
    ]);

    const result = await getCorrections('there house');
    const ctx = result.find((c) => c.original === 'there');
    expect(ctx).toBeDefined();
    expect(ctx!.type).toBe('confusion');
    expect(ctx!.suggested).toBe('their');
  });

  // ── Merging from multiple sources ──────────────────────────────────
  it('merges corrections from multiple sources, removes overlapping ranges', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);
    mockCheckGrammar.mockReturnValue([
      {
        original: 'h',
        suggested: 'H',
        type: 'grammar',
        start: 10,
        end: 11,
        confidence: 0.75,
        explanation: 'Capitalize.',
      },
    ]);
    mockCheckContext.mockReturnValue([
      {
        original: 'there',
        suggested: 'their',
        type: 'confusion',
        start: 15,
        end: 20,
        confidence: 0.75,
        explanation: 'Possession.',
      },
    ]);

    const result = await getCorrections('teh cat is hello. there house');
    expect(result.length).toBe(3);
  });

  // ── Personal dictionary filtering ─────────────────────────────────
  it('skips words in personal dictionary', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);
    mockIsPersonal.mockImplementation((word: string) =>
      word.toLowerCase() === 'teh'
    );

    const result = await getCorrections('teh cat');
    const spelling = result.find((c) => c.original === 'teh');
    expect(spelling).toBeUndefined();
  });

  // ── Cloud API fallback ─────────────────────────────────────────────
  it('falls back to cloud API when all local checks return empty', async () => {
    mockApiCorrections.mockResolvedValue({
      data: {
        corrections: [
          {
            original: 'becuase',
            correction: 'because',
            error_type: 'spelling',
            position: { start: 0, end: 7 },
            confidence: 0.95,
            explanation: 'Common misspelling.',
          },
        ],
      },
    } as any);

    const result = await getCorrections('becuase');
    expect(mockApiCorrections).toHaveBeenCalledWith('becuase');
    expect(result.length).toBe(1);
    expect(result[0].suggested).toBe('because');
  });

  it('returns [] when cloud API throws', async () => {
    mockApiCorrections.mockRejectedValue(new Error('Network error'));

    const result = await getCorrections('becuase');
    expect(result).toEqual([]);
  });

  it('does NOT call cloud API when local corrections are found', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);

    await getCorrections('teh cat');
    expect(mockApiCorrections).not.toHaveBeenCalled();
  });

  // ── Overlap removal ────────────────────────────────────────────────
  it('when spelling and grammar corrections overlap, only the first by start position survives', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);
    mockCheckGrammar.mockReturnValue([
      {
        original: 'teh the',
        suggested: 'the',
        type: 'grammar',
        start: 0,
        end: 7,
        confidence: 0.85,
        explanation: 'Doubled word after fix.',
      },
    ]);

    const result = await getCorrections('teh the cat');
    // Both start at 0; sorting by start then larger span means grammar (0-7) comes first,
    // but the overlap check removes whichever comes second
    const atZero = result.filter((c) => c.start === 0);
    expect(atZero.length).toBe(1);
  });

  // ── Priority ordering ─────────────────────────────────────────────
  it('spelling corrections survive over context and grammar at the same position', async () => {
    // Spelling at position 0-3
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);
    // Context at same position 0-3
    mockCheckContext.mockReturnValue([
      {
        original: 'teh',
        suggested: 'tea',
        type: 'confusion',
        start: 0,
        end: 3,
        confidence: 0.7,
        explanation: 'Possible confusion.',
      },
    ]);
    // Grammar at same position 0-3
    mockCheckGrammar.mockReturnValue([
      {
        original: 'teh',
        suggested: 'Teh',
        type: 'grammar',
        start: 0,
        end: 3,
        confidence: 0.6,
        explanation: 'Capitalize.',
      },
    ]);

    const result = await getCorrections('teh cat');
    const atZero = result.filter((c) => c.start === 0);
    expect(atZero.length).toBe(1);
    // mergeCorrections receives groups in order: spelling, context, grammar
    // All three have same start=0, end=3 (same span), so sort is stable by insertion.
    // The first one encountered wins (spelling).
    expect(atZero[0].type).toBe('spelling');
    expect(atZero[0].suggested).toBe('the');
  });

  // ── Required fields ────────────────────────────────────────────────
  it('all returned corrections have required fields', async () => {
    mockRunLocal.mockResolvedValue([
      {
        original: 'teh',
        correction: 'the',
        confidence: 0.9,
        position: { start: 0, end: 3 },
        errorType: 'spelling',
      },
    ]);
    mockCheckGrammar.mockReturnValue([
      {
        original: 'h',
        suggested: 'H',
        type: 'grammar',
        start: 10,
        end: 11,
        confidence: 0.8,
        explanation: 'Capitalize.',
      },
    ]);

    const result = await getCorrections('teh cat is hello world');
    for (const c of result) {
      expect(c).toHaveProperty('original');
      expect(c).toHaveProperty('suggested');
      expect(c).toHaveProperty('type');
      expect(c).toHaveProperty('start');
      expect(c).toHaveProperty('end');
      expect(c).toHaveProperty('confidence');
      expect(typeof c.original).toBe('string');
      expect(typeof c.suggested).toBe('string');
      expect(typeof c.start).toBe('number');
      expect(typeof c.end).toBe('number');
      expect(typeof c.confidence).toBe('number');
    }
  });
});
