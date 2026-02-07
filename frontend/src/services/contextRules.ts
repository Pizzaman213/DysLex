/**
 * Sentence-level context rules for resolving confusion pairs.
 *
 * Uses surrounding words to detect when a homophone or near-homophone is used
 * in the wrong context and suggests the correct alternative.
 */

export interface ContextCorrection {
  original: string;
  suggested: string;
  type: 'confusion';
  start: number;
  end: number;
  confidence: number;
  explanation: string;
}

interface Token {
  word: string;
  lower: string;
  start: number;
  end: number;
}

function tokenizeWithPositions(text: string): Token[] {
  const tokens: Token[] = [];
  const regex = /\b[\w']+\b/g;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    tokens.push({
      word: match[0],
      lower: match[0].toLowerCase(),
      start: match.index,
      end: match.index + match[0].length,
    });
  }
  return tokens;
}

// ── their / there / they're ────────────────────────────────────────────

const NOUNS_AFTER_POSSESSIVE = new Set([
  'house', 'home', 'car', 'dog', 'cat', 'name', 'mom', 'dad', 'mother',
  'father', 'brother', 'sister', 'family', 'friend', 'friends', 'teacher',
  'school', 'work', 'job', 'money', 'food', 'room', 'door', 'phone',
  'book', 'books', 'stuff', 'things', 'way', 'time', 'life', 'lives',
  'child', 'children', 'son', 'daughter', 'parents', 'team', 'group',
  'own', 'best', 'new', 'old', 'first', 'last', 'big',
]);

const DIRECTIONAL_WORDS = new Set([
  'over', 'out', 'up', 'down', 'right', 'back', 'around', 'near', 'from',
  'go', 'went', 'going', 'been', 'is', 'are', 'was', 'were',
]);

function checkTheirThere(tokens: Token[]): ContextCorrection[] {
  const corrections: ContextCorrection[] = [];

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const next = tokens[i + 1];
    const prev = tokens[i - 1];

    if (t.lower === 'there' && next) {
      // "there house" -> "their house" (possessive context)
      if (NOUNS_AFTER_POSSESSIVE.has(next.lower)) {
        corrections.push({
          original: t.word,
          suggested: 'their',
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.75,
          explanation: 'Use "their" to show something belongs to them.',
        });
      }
      // "there going" / "there doing" -> "they're" (verb-ing follows)
      if (next.lower.endsWith('ing') || next.lower === 'not' || next.lower === 'gonna' || next.lower === 'always' || next.lower === 'never') {
        corrections.push({
          original: t.word,
          suggested: "they're",
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.75,
          explanation: '"they\'re" is short for "they are".',
        });
      }
    }

    if (t.lower === 'their' && prev) {
      // "over their" -> "over there" (directional context)
      if (DIRECTIONAL_WORDS.has(prev.lower)) {
        corrections.push({
          original: t.word,
          suggested: 'there',
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.75,
          explanation: 'Use "there" to talk about a place.',
        });
      }
    }

    if (t.lower === 'their' && next) {
      // "their going" -> "they're going" (verb-ing follows)
      if (next.lower.endsWith('ing') || next.lower === 'not' || next.lower === 'gonna') {
        corrections.push({
          original: t.word,
          suggested: "they're",
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.75,
          explanation: '"they\'re" is short for "they are".',
        });
      }
    }
  }
  return corrections;
}

// ── your / you're ──────────────────────────────────────────────────────

const VERB_FOLLOWERS = new Set([
  'going', 'doing', 'being', 'getting', 'making', 'coming', 'running',
  'looking', 'saying', 'trying', 'taking', 'thinking', 'telling',
  'not', 'gonna', 'always', 'never', 'welcome', 'right', 'wrong',
  'sure', 'ready', 'late', 'early',
]);

function checkYourYoure(tokens: Token[]): ContextCorrection[] {
  const corrections: ContextCorrection[] = [];

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const next = tokens[i + 1];

    if (t.lower === 'your' && next) {
      if (VERB_FOLLOWERS.has(next.lower) || next.lower.endsWith('ing')) {
        corrections.push({
          original: t.word,
          suggested: "you're",
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.75,
          explanation: '"you\'re" is short for "you are".',
        });
      }
    }
  }
  return corrections;
}

// ── to / too / two ─────────────────────────────────────────────────────

const TOO_ADJECTIVES = new Set([
  'much', 'many', 'big', 'small', 'fast', 'slow', 'hard', 'easy', 'hot',
  'cold', 'long', 'short', 'loud', 'quiet', 'far', 'close', 'late',
  'early', 'old', 'young', 'high', 'low', 'good', 'bad', 'tired',
  'busy', 'expensive', 'cheap', 'heavy', 'light', 'dark', 'bright',
  'difficult', 'simple', 'complicated',
]);

const TOO_CLAUSE_END = new Set([
  'me', 'us', 'them', 'him', 'her',
]);

function checkToToo(tokens: Token[]): ContextCorrection[] {
  const corrections: ContextCorrection[] = [];

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const next = tokens[i + 1];
    const prev = tokens[i - 1];

    if (t.lower === 'to') {
      // "to much" -> "too much"
      if (next && TOO_ADJECTIVES.has(next.lower)) {
        corrections.push({
          original: t.word,
          suggested: 'too',
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.8,
          explanation: 'Use "too" to mean "excessively" or "also".',
        });
      }
      // "me to" at end of clause/sentence -> "me too"
      if (prev && TOO_CLAUSE_END.has(prev.lower)) {
        const isEndOfClause = !next || /^[.!?,;]/.test(next.word);
        if (isEndOfClause) {
          corrections.push({
            original: t.word,
            suggested: 'too',
            type: 'confusion',
            start: t.start,
            end: t.end,
            confidence: 0.75,
            explanation: 'Use "too" to mean "also".',
          });
        }
      }
    }
  }
  return corrections;
}

// ── then / than ────────────────────────────────────────────────────────

const COMPARATIVES = new Set([
  'more', 'less', 'better', 'worse', 'bigger', 'smaller', 'faster',
  'slower', 'harder', 'easier', 'higher', 'lower', 'longer', 'shorter',
  'older', 'younger', 'newer', 'greater', 'fewer', 'rather', 'other',
  'taller', 'wider', 'deeper', 'stronger', 'weaker', 'smarter',
  'nicer', 'larger', 'further', 'farther',
]);

function checkThenThan(tokens: Token[]): ContextCorrection[] {
  const corrections: ContextCorrection[] = [];

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    const prev = tokens[i - 1];

    if (t.lower === 'then' && prev) {
      // "more then" -> "more than" (comparative context)
      if (COMPARATIVES.has(prev.lower) || prev.lower.endsWith('er')) {
        corrections.push({
          original: t.word,
          suggested: 'than',
          type: 'confusion',
          start: t.start,
          end: t.end,
          confidence: 0.8,
          explanation: 'Use "than" for comparisons. "Then" is about time.',
        });
      }
    }
  }
  return corrections;
}

// ── Public API ──────────────────────────────────────────────────────────

export function checkContextualConfusions(text: string): ContextCorrection[] {
  if (!text.trim()) return [];

  const tokens = tokenizeWithPositions(text);

  return [
    ...checkTheirThere(tokens),
    ...checkYourYoure(tokens),
    ...checkToToo(tokens),
    ...checkThenThan(tokens),
  ];
}
