/**
 * Readability Utilities
 *
 * Client-side Flesch-Kincaid readability calculations
 */

export interface ReadabilityMetrics {
  grade: number;
  readingEase: number;
  wordCount: number;
  sentenceCount: number;
  avgSentenceLength: number;
  level: 'easy' | 'medium' | 'advanced';
}

/**
 * Count syllables in a word using heuristic rules
 */
export function countSyllables(word: string): number {
  word = word.toLowerCase().trim();
  if (word.length === 0) return 0;
  if (word.length <= 3) return 1;

  // Remove non-alphabetic characters
  word = word.replace(/[^a-z]/g, '');

  // Count vowel groups
  const vowelGroups = word.match(/[aeiouy]+/g);
  let count = vowelGroups ? vowelGroups.length : 0;

  // Subtract silent e at the end
  if (word.endsWith('e')) count--;

  // Ensure at least 1 syllable
  return Math.max(count, 1);
}

/**
 * Calculate Flesch-Kincaid Grade Level
 * Formula: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
 */
export function calculateFleschKincaidGrade(text: string): number {
  const { wordCount, sentenceCount } = parseText(text);

  if (wordCount === 0 || sentenceCount === 0) return 0;

  const words = text.match(/\b[a-z]+\b/gi) || [];
  const totalSyllables = words.reduce((sum, word) => sum + countSyllables(word), 0);

  const syllablesPerWord = totalSyllables / wordCount;
  const wordsPerSentence = wordCount / sentenceCount;

  const grade = 0.39 * wordsPerSentence + 11.8 * syllablesPerWord - 15.59;

  return Math.max(0, Math.round(grade * 10) / 10);
}

/**
 * Calculate Flesch Reading Ease Score
 * Formula: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
 */
export function calculateFleschReadingEase(text: string): number {
  const { wordCount, sentenceCount } = parseText(text);

  if (wordCount === 0 || sentenceCount === 0) return 0;

  const words = text.match(/\b[a-z]+\b/gi) || [];
  const totalSyllables = words.reduce((sum, word) => sum + countSyllables(word), 0);

  const syllablesPerWord = totalSyllables / wordCount;
  const wordsPerSentence = wordCount / sentenceCount;

  const ease = 206.835 - 1.015 * wordsPerSentence - 84.6 * syllablesPerWord;

  return Math.max(0, Math.round(ease * 10) / 10);
}

/**
 * Get readability level from grade
 */
export function getReadabilityLevel(grade: number): 'easy' | 'medium' | 'advanced' {
  if (grade <= 8) return 'easy';
  if (grade <= 12) return 'medium';
  return 'advanced';
}

/**
 * Parse text to extract basic metrics
 */
export function parseText(text: string): { wordCount: number; sentenceCount: number } {
  // Remove HTML tags if any
  const cleanText = text.replace(/<[^>]*>/g, ' ');

  // Count words (sequences of alphanumeric characters)
  const words = cleanText.match(/\b[a-z0-9]+\b/gi) || [];
  const wordCount = words.length;

  // Count sentences (end with . ! ?)
  const sentences = cleanText.match(/[.!?]+/g) || [];
  const sentenceCount = Math.max(sentences.length, 1); // At least 1 sentence

  return { wordCount, sentenceCount };
}

/**
 * Analyze text and return full readability metrics
 */
export function analyzeText(text: string): ReadabilityMetrics {
  const { wordCount, sentenceCount } = parseText(text);
  const grade = calculateFleschKincaidGrade(text);
  const readingEase = calculateFleschReadingEase(text);
  const avgSentenceLength = wordCount > 0 ? Math.round((wordCount / sentenceCount) * 10) / 10 : 0;
  const level = getReadabilityLevel(grade);

  return {
    grade,
    readingEase,
    wordCount,
    sentenceCount,
    avgSentenceLength,
    level
  };
}
