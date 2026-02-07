import { describe, it, expect } from 'vitest';
import { checkContextualConfusions } from '@/services/contextRules';

describe('checkContextualConfusions', () => {
  // ── Empty / whitespace input ────────────────────────────────────────
  it('returns [] for empty string', () => {
    expect(checkContextualConfusions('')).toEqual([]);
  });

  it('returns [] for whitespace-only string', () => {
    expect(checkContextualConfusions('   ')).toEqual([]);
  });

  // ── their / there / they're ────────────────────────────────────────
  describe('their / there / they\'re', () => {
    it('"there house is big" suggests "their"', () => {
      const results = checkContextualConfusions('there house is big');
      const match = results.filter(
        (c) => c.original === 'there' && c.suggested === 'their'
      );
      expect(match.length).toBe(1);
    });

    it('"there going home" suggests "they\'re"', () => {
      const results = checkContextualConfusions('there going home');
      const match = results.filter(
        (c) => c.original === 'there' && c.suggested === "they're"
      );
      expect(match.length).toBe(1);
    });

    it('"over their" suggests "there"', () => {
      const results = checkContextualConfusions('over their');
      const match = results.filter(
        (c) => c.original === 'their' && c.suggested === 'there'
      );
      expect(match.length).toBe(1);
    });

    it('"their going home" suggests "they\'re"', () => {
      const results = checkContextualConfusions('their going home');
      const match = results.filter(
        (c) => c.original === 'their' && c.suggested === "they're"
      );
      expect(match.length).toBe(1);
    });
  });

  // ── your / you're ──────────────────────────────────────────────────
  describe("your / you're", () => {
    it('"your going home" suggests "you\'re"', () => {
      const results = checkContextualConfusions('your going home');
      const match = results.filter(
        (c) => c.original === 'your' && c.suggested === "you're"
      );
      expect(match.length).toBe(1);
    });

    it('does not flag correct usage "your house"', () => {
      const results = checkContextualConfusions('your house');
      const match = results.filter(
        (c) => c.original === 'your'
      );
      expect(match.length).toBe(0);
    });
  });

  // ── to / too ───────────────────────────────────────────────────────
  describe('to / too', () => {
    it('"to much food" suggests "too"', () => {
      const results = checkContextualConfusions('to much food');
      const match = results.filter(
        (c) => c.original === 'to' && c.suggested === 'too'
      );
      expect(match.length).toBe(1);
    });

    it('"me to" at end of text suggests "too"', () => {
      const results = checkContextualConfusions('me to');
      const match = results.filter(
        (c) => c.original === 'to' && c.suggested === 'too'
      );
      expect(match.length).toBe(1);
    });
  });

  // ── then / than ────────────────────────────────────────────────────
  describe('then / than', () => {
    it('"more then ever" suggests "than"', () => {
      const results = checkContextualConfusions('more then ever');
      const match = results.filter(
        (c) => c.original === 'then' && c.suggested === 'than'
      );
      expect(match.length).toBe(1);
    });

    it('"bigger then me" suggests "than" (prev word ends in "er")', () => {
      const results = checkContextualConfusions('bigger then me');
      const match = results.filter(
        (c) => c.original === 'then' && c.suggested === 'than'
      );
      expect(match.length).toBe(1);
    });
  });

  // ── Correct usage (no false positives) ─────────────────────────────
  it('does not flag correct usage of "their house"', () => {
    const results = checkContextualConfusions('their house');
    // "their house" is possessive + noun, which is correct usage.
    // The checkTheirThere function does NOT flag "their" + noun as wrong.
    const wrongFlags = results.filter(
      (c) => c.original === 'their' && c.suggested !== 'their'
    );
    expect(wrongFlags.length).toBe(0);
  });

  // ── Position accuracy ──────────────────────────────────────────────
  it('reports accurate start and end positions matching word positions', () => {
    const text = 'there house is big';
    const results = checkContextualConfusions(text);
    const match = results.find(
      (c) => c.original === 'there' && c.suggested === 'their'
    );
    expect(match).toBeDefined();
    // "there" starts at index 0 and ends at index 5
    expect(match!.start).toBe(0);
    expect(match!.end).toBe(5);
    expect(text.slice(match!.start, match!.end)).toBe('there');

    // Also verify type and confidence
    expect(match!.type).toBe('confusion');
    expect(match!.confidence).toBeGreaterThan(0);
    expect(match!.explanation.length).toBeGreaterThan(0);
  });
});
