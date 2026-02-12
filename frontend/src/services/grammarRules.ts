/**
 * Client-side grammar rules engine (regex-based fallback).
 *
 * These regex rules act as a fallback when the ONNX model is unavailable.
 * When the model IS loaded, it handles grammar corrections with full
 * contextual understanding (subject-verb agreement, articles, tense, etc.).
 * The correction merge logic in correctionService.ts gives model-based
 * grammar corrections priority over these regex-based ones.
 *
 * Each rule returns corrections with type 'grammar', position info, and a
 * friendly explanation.
 */

export interface GrammarCorrection {
  original: string;
  suggested: string;
  type: 'grammar';
  start: number;
  end: number;
  confidence: number;
  explanation: string;
}

// ── Rule 1: Doubled words ──────────────────────────────────────────────

const DOUBLED_WORD_ALLOWLIST = new Set([
  'had', 'that', 'do', 'is', 'was', 'bye', 'no', 'so', 'boo', 'poo',
]);

function checkDoubledWords(text: string): GrammarCorrection[] {
  const corrections: GrammarCorrection[] = [];
  const regex = /\b(\w+)\s+(\1)\b/gi;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const word = match[1].toLowerCase();
    if (DOUBLED_WORD_ALLOWLIST.has(word)) continue;

    corrections.push({
      original: match[0],
      suggested: match[1],
      type: 'grammar',
      start: match.index,
      end: match.index + match[0].length,
      confidence: 0.9,
      explanation: `"${match[1]}" appears twice in a row — you probably only need it once.`,
    });
  }
  return corrections;
}

// ── Rule 2: a / an ─────────────────────────────────────────────────────

// Words starting with a silent h or vowel sound that need "an"
const AN_EXCEPTIONS = new Set([
  'hour', 'hours', 'honest', 'honestly', 'honor', 'honors', 'honour',
  'honours', 'heir', 'heirs', 'herb', 'herbs', 'homage',
]);

// Words starting with a vowel letter but consonant sound that need "a"
const A_EXCEPTIONS = new Set([
  'university', 'uniform', 'union', 'unique', 'unit', 'united', 'universal',
  'universe', 'unicorn', 'unilateral', 'uranium', 'urinal', 'usage', 'use',
  'used', 'useful', 'user', 'usual', 'usually', 'utility', 'utensil',
  'one', 'once', 'european', 'eulogy',
]);

function checkAAnUsage(text: string): GrammarCorrection[] {
  const corrections: GrammarCorrection[] = [];
  // Match "a" or "an" followed by a word
  const regex = /\b(a|an)\s+(\w+)\b/gi;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const article = match[1].toLowerCase();
    const nextWord = match[2].toLowerCase();
    const startsWithVowel = /^[aeiou]/i.test(nextWord);

    let needsAn: boolean;
    if (AN_EXCEPTIONS.has(nextWord)) {
      needsAn = true;
    } else if (A_EXCEPTIONS.has(nextWord)) {
      needsAn = false;
    } else {
      needsAn = startsWithVowel;
    }

    const correctArticle = needsAn ? 'an' : 'a';
    if (article !== correctArticle) {
      // Preserve original casing of the article
      const suggestedArticle = match[1][0] === match[1][0].toUpperCase()
        ? correctArticle.charAt(0).toUpperCase() + correctArticle.slice(1)
        : correctArticle;

      corrections.push({
        original: match[0],
        suggested: `${suggestedArticle} ${match[2]}`,
        type: 'grammar',
        start: match.index,
        end: match.index + match[0].length,
        confidence: 0.85,
        explanation: needsAn
          ? `Use "an" before words that start with a vowel sound, like "${nextWord}".`
          : `Use "a" before words that start with a consonant sound, like "${nextWord}".`,
      });
    }
  }
  return corrections;
}

// ── Rule 3: Sentence capitalization ────────────────────────────────────

function checkCapitalization(text: string): GrammarCorrection[] {
  const corrections: GrammarCorrection[] = [];
  const regex = /([.!?])\s+([a-z])/g;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const lowerChar = match[2];
    // Only mark the single character that needs capitalizing, not the punctuation/space
    const charIndex = match.index + match[0].length - 1;

    corrections.push({
      original: lowerChar,
      suggested: lowerChar.toUpperCase(),
      type: 'grammar',
      start: charIndex,
      end: charIndex + 1,
      confidence: 0.8,
      explanation: 'Sentences should start with a capital letter.',
    });
  }

  // Also check the very first character of the text
  if (text.length > 0 && /^[a-z]/.test(text)) {
    corrections.push({
      original: text[0],
      suggested: text[0].toUpperCase(),
      type: 'grammar',
      start: 0,
      end: 1,
      confidence: 0.75,
      explanation: 'The first word should start with a capital letter.',
    });
  }

  return corrections;
}

// ── Rule 4: Subject-verb agreement (pronoun + verb) ────────────────────

const SUBJECT_VERB_FIXES: Record<string, Record<string, string>> = {
  // singular subjects needing singular verbs
  'he': { 'go': 'goes', 'do': 'does', 'have': 'has', 'run': 'runs', 'come': 'comes', 'make': 'makes', 'take': 'takes', 'say': 'says', 'get': 'gets', 'give': 'gives', 'know': 'knows', 'think': 'thinks', 'want': 'wants', 'need': 'needs', 'like': 'likes', 'see': 'sees', 'look': 'looks', 'seem': 'seems', 'feel': 'feels' },
  'she': { 'go': 'goes', 'do': 'does', 'have': 'has', 'run': 'runs', 'come': 'comes', 'make': 'makes', 'take': 'takes', 'say': 'says', 'get': 'gets', 'give': 'gives', 'know': 'knows', 'think': 'thinks', 'want': 'wants', 'need': 'needs', 'like': 'likes', 'see': 'sees', 'look': 'looks', 'seem': 'seems', 'feel': 'feels' },
  'it': { 'go': 'goes', 'do': 'does', 'have': 'has', 'run': 'runs', 'come': 'comes', 'make': 'makes', 'take': 'takes', 'say': 'says', 'get': 'gets', 'give': 'gives', 'know': 'knows', 'think': 'thinks', 'want': 'wants', 'need': 'needs', 'like': 'likes', 'see': 'sees', 'look': 'looks', 'seem': 'seems', 'feel': 'feels' },
  // plural subjects needing plural verbs
  'they': { 'goes': 'go', 'does': 'do', 'has': 'have', 'runs': 'run', 'comes': 'come', 'makes': 'make', 'takes': 'take', 'says': 'say', 'gets': 'get', 'gives': 'give', 'knows': 'know', 'thinks': 'think', 'wants': 'want', 'needs': 'need', 'likes': 'like', 'sees': 'see', 'looks': 'look', 'seems': 'seem', 'feels': 'feel' },
  'we': { 'goes': 'go', 'does': 'do', 'has': 'have', 'runs': 'run', 'comes': 'come', 'makes': 'make', 'takes': 'take', 'says': 'say', 'gets': 'get', 'gives': 'give', 'knows': 'know', 'thinks': 'think', 'wants': 'want', 'needs': 'need', 'likes': 'like', 'sees': 'see', 'looks': 'look', 'seems': 'seem', 'feels': 'feel' },
  'i': { 'goes': 'go', 'does': 'do', 'has': 'have', 'runs': 'run', 'comes': 'come', 'makes': 'make', 'takes': 'take', 'says': 'say', 'gets': 'get', 'gives': 'give', 'knows': 'know', 'thinks': 'think', 'wants': 'want', 'needs': 'need', 'likes': 'like', 'sees': 'see', 'looks': 'look', 'seems': 'seem', 'feels': 'feel' },
};

function checkSubjectVerb(text: string): GrammarCorrection[] {
  const corrections: GrammarCorrection[] = [];
  const regex = /\b(\w+)\s+(\w+)\b/gi;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const subject = match[1].toLowerCase();
    const verb = match[2].toLowerCase();

    const fixes = SUBJECT_VERB_FIXES[subject];
    if (fixes && fixes[verb]) {
      corrections.push({
        original: match[0],
        suggested: `${match[1]} ${fixes[verb]}`,
        type: 'grammar',
        start: match.index,
        end: match.index + match[0].length,
        confidence: 0.85,
        explanation: `With "${match[1]}", use "${fixes[verb]}" instead of "${match[2]}".`,
      });
    }
  }
  return corrections;
}

// ── Rule 5: its / it's ─────────────────────────────────────────────────

// Words that commonly follow "it's" (contraction of "it is" or "it has")
const ITS_VERB_FOLLOWERS = new Set([
  'a', 'an', 'the', 'not', 'been', 'going', 'being', 'getting', 'about',
  'just', 'really', 'so', 'very', 'quite', 'too', 'also', 'still',
  'already', 'always', 'never', 'only', 'hard', 'easy', 'good', 'bad',
  'great', 'nice', 'fine', 'okay', 'ok', 'important', 'possible',
  'impossible', 'clear', 'obvious', 'true', 'time', 'like', 'my',
]);

function checkItsVsIts(text: string): GrammarCorrection[] {
  const corrections: GrammarCorrection[] = [];

  // Check "its" that should be "it's"
  const itsRegex = /\bits\s+(\w+)/gi;
  let match: RegExpExecArray | null;

  while ((match = itsRegex.exec(text)) !== null) {
    const nextWord = match[1].toLowerCase();
    if (ITS_VERB_FOLLOWERS.has(nextWord) || nextWord.endsWith('ing')) {
      corrections.push({
        original: `its ${match[1]}`,
        suggested: `it's ${match[1]}`,
        type: 'grammar',
        start: match.index,
        end: match.index + match[0].length,
        confidence: 0.75,
        explanation: '"it\'s" is short for "it is" or "it has". "its" shows possession (like "his" or "her").',
      });
    }
  }

  return corrections;
}

// ── Rule 6: Missing end punctuation ────────────────────────────────────

function checkMissingPeriod(text: string): GrammarCorrection[] {
  const trimmed = text.trimEnd();
  if (trimmed.length < 20) return [];
  if (/[.!?…:;]$/.test(trimmed)) return [];
  // Don't flag if text looks like a heading/title (no sentence structure)
  if (!trimmed.includes(' ')) return [];

  return [{
    original: trimmed.slice(-1),
    suggested: trimmed.slice(-1) + '.',
    type: 'grammar',
    start: trimmed.length - 1,
    end: trimmed.length,
    confidence: 0.6,
    explanation: 'Sentences usually end with a period, question mark, or exclamation point.',
  }];
}

// ── Public API ──────────────────────────────────────────────────────────

export function checkGrammar(text: string): GrammarCorrection[] {
  if (!text.trim()) return [];

  return [
    ...checkDoubledWords(text),
    ...checkAAnUsage(text),
    ...checkCapitalization(text),
    ...checkSubjectVerb(text),
    ...checkItsVsIts(text),
    ...checkMissingPeriod(text),
  ];
}
