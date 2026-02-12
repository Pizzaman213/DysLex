import { describe, it, expect } from 'vitest';
import { checkGrammar } from '@/services/grammarRules';

describe('checkGrammar', () => {
  // ── Empty / whitespace input ────────────────────────────────────────
  it('returns [] for empty string', () => {
    expect(checkGrammar('')).toEqual([]);
  });

  it('returns [] for whitespace-only string', () => {
    expect(checkGrammar('   ')).toEqual([]);
  });

  // ── Rule 1: Doubled words ──────────────────────────────────────────
  describe('doubled words', () => {
    it('flags "the the cat" and suggests "the"', () => {
      const results = checkGrammar('the the cat');
      const doubled = results.filter(
        (c) => c.original.toLowerCase() === 'the the'
      );
      expect(doubled.length).toBe(1);
      expect(doubled[0].suggested).toBe('the');
    });

    it('does not flag allowlisted doubled words like "had had"', () => {
      const results = checkGrammar('he had had enough');
      const doubled = results.filter(
        (c) => c.original.toLowerCase() === 'had had'
      );
      expect(doubled.length).toBe(0);
    });
  });

  // ── Rule 2: a / an ────────────────────────────────────────────────
  describe('a/an usage', () => {
    it('flags "a apple" and suggests "an apple"', () => {
      const results = checkGrammar('a apple');
      const aAn = results.filter((c) => c.original === 'a apple');
      expect(aAn.length).toBe(1);
      expect(aAn[0].suggested).toBe('an apple');
    });

    it('flags "an university" and suggests "a university"', () => {
      const results = checkGrammar('an university');
      const aAn = results.filter((c) => c.original === 'an university');
      expect(aAn.length).toBe(1);
      expect(aAn[0].suggested).toBe('a university');
    });

    it('flags "a hour" and suggests "an hour" (silent h)', () => {
      const results = checkGrammar('a hour');
      const aAn = results.filter((c) => c.original === 'a hour');
      expect(aAn.length).toBe(1);
      expect(aAn[0].suggested).toBe('an hour');
    });

    it('does not flag correct usage "a cat"', () => {
      const results = checkGrammar('A cat');
      const aAn = results.filter(
        (c) =>
          c.original.toLowerCase().includes('a cat') &&
          c.explanation?.includes('vowel')
      );
      expect(aAn.length).toBe(0);
    });
  });

  // ── Rule 3: Capitalization ─────────────────────────────────────────
  describe('capitalization', () => {
    it('flags lowercase letter after period', () => {
      const results = checkGrammar('Hello. the dog');
      const caps = results.filter(
        (c) => c.explanation === 'Sentences should start with a capital letter.'
      );
      expect(caps.length).toBe(1);
      expect(caps[0].original).toBe('t');
      expect(caps[0].suggested).toBe('T');
    });

    it('flags first character lowercase', () => {
      const results = checkGrammar('hello world');
      const caps = results.filter(
        (c) =>
          c.explanation === 'The first word should start with a capital letter.'
      );
      expect(caps.length).toBe(1);
      expect(caps[0].original).toBe('h');
      expect(caps[0].suggested).toBe('H');
      expect(caps[0].start).toBe(0);
      expect(caps[0].end).toBe(1);
    });

    it('does not flag correct capitalization', () => {
      const results = checkGrammar('Hello. The dog');
      const caps = results.filter(
        (c) =>
          c.explanation === 'Sentences should start with a capital letter.' ||
          c.explanation === 'The first word should start with a capital letter.'
      );
      expect(caps.length).toBe(0);
    });
  });

  // ── Rule 4: Subject-verb agreement ─────────────────────────────────
  describe('subject-verb agreement', () => {
    it('flags "he go home" and suggests "he goes"', () => {
      const results = checkGrammar('He go home');
      const sv = results.filter(
        (c) =>
          c.original.toLowerCase() === 'he go' &&
          c.suggested.toLowerCase().includes('goes')
      );
      expect(sv.length).toBe(1);
    });

    it('flags "they goes home" and suggests "they go"', () => {
      const results = checkGrammar('They goes home');
      const sv = results.filter(
        (c) =>
          c.original.toLowerCase() === 'they goes' &&
          c.suggested.toLowerCase().includes('go')
      );
      expect(sv.length).toBe(1);
    });

    it('does not flag correct "he goes"', () => {
      const results = checkGrammar('He goes');
      const sv = results.filter(
        (c) => c.original.toLowerCase() === 'he goes'
      );
      expect(sv.length).toBe(0);
    });
  });

  // ── Rule 5: its / it's ────────────────────────────────────────────
  describe("its / it's", () => {
    it('flags "its going well" and suggests "it\'s going"', () => {
      const results = checkGrammar('its going well');
      const its = results.filter(
        (c) => c.original === 'its going' && c.suggested === "it's going"
      );
      expect(its.length).toBe(1);
    });

    it('flags "its a great day" and suggests "it\'s a great day"', () => {
      const results = checkGrammar('its a great day');
      const its = results.filter(
        (c) => c.original === 'its a' && c.suggested === "it's a"
      );
      expect(its.length).toBe(1);
    });
  });

  // ── Rule 6: Missing period ────────────────────────────────────────
  describe('missing period', () => {
    it('flags long text without ending punctuation', () => {
      const text = 'This is a long sentence without a period at the end';
      const results = checkGrammar(text);
      const period = results.filter(
        (c) =>
          c.explanation ===
          'Sentences usually end with a period, question mark, or exclamation point.'
      );
      expect(period.length).toBe(1);
    });

    it('does not flag short text', () => {
      const results = checkGrammar('hello');
      const period = results.filter(
        (c) =>
          c.explanation ===
          'Sentences usually end with a period, question mark, or exclamation point.'
      );
      expect(period.length).toBe(0);
    });
  });

  // ── General correction shape ──────────────────────────────────────
  it('all corrections have valid start < end, confidence > 0, and non-empty explanation', () => {
    const inputs = [
      'the the cat',
      'a apple',
      'hello. the dog',
      'he go home',
      'its going well',
      'This is a sentence without a period at the end',
    ];

    for (const input of inputs) {
      const results = checkGrammar(input);
      for (const c of results) {
        expect(c.start).toBeLessThan(c.end);
        expect(c.confidence).toBeGreaterThan(0);
        expect(c.explanation.length).toBeGreaterThan(0);
        expect(c.type).toBe('grammar');
      }
    }
  });
});
