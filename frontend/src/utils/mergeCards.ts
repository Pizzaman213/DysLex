/**
 * Card merge utility for the final extraction pass after brainstorming.
 *
 * Merges brainstorm-generated cards with extraction results:
 * - Title similarity matching (case-insensitive word overlap)
 * - Sub-idea dedup by title
 * - Preserves manually-edited cards
 */

interface SubIdea {
  id: string;
  title: string;
  body: string;
}

interface ThoughtCard {
  id: string;
  title: string;
  body: string;
  sub_ideas: SubIdea[];
}

/**
 * Compute word overlap ratio between two titles.
 * Returns a value between 0 and 1 where 1 = identical word set.
 */
function titleSimilarity(a: string, b: string): number {
  const wordsA = new Set(a.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(Boolean));
  const wordsB = new Set(b.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(Boolean));

  if (wordsA.size === 0 || wordsB.size === 0) return 0;

  let overlap = 0;
  for (const w of wordsA) {
    if (wordsB.has(w)) overlap++;
  }

  const union = new Set([...wordsA, ...wordsB]).size;
  return union > 0 ? overlap / union : 0;
}

const SIMILARITY_THRESHOLD = 0.5;

/**
 * Deduplicate sub-ideas by title (case-insensitive).
 */
function deduplicateSubIdeas(subs: SubIdea[]): SubIdea[] {
  const seen = new Set<string>();
  const result: SubIdea[] = [];

  for (const sub of subs) {
    const key = sub.title.toLowerCase().trim();
    if (key && !seen.has(key)) {
      seen.add(key);
      result.push(sub);
    }
  }

  return result;
}

/**
 * Merge brainstorm-generated cards with fresh extraction results.
 *
 * Strategy:
 * 1. For each extraction card, look for a similar brainstorm card
 * 2. If found, merge sub-ideas and use the longer body
 * 3. If no match, add the extraction card as new
 * 4. Keep brainstorm cards that have no match in extraction (user's unique ideas)
 */
export function mergeCards(
  brainstormCards: ThoughtCard[],
  extractionCards: ThoughtCard[],
): ThoughtCard[] {
  const merged: ThoughtCard[] = [];
  const matchedBrainstormIds = new Set<string>();

  for (const extCard of extractionCards) {
    let bestMatch: ThoughtCard | null = null;
    let bestScore = 0;

    for (const bsCard of brainstormCards) {
      if (matchedBrainstormIds.has(bsCard.id)) continue;

      const score = titleSimilarity(extCard.title, bsCard.title);
      if (score > bestScore && score >= SIMILARITY_THRESHOLD) {
        bestScore = score;
        bestMatch = bsCard;
      }
    }

    if (bestMatch) {
      matchedBrainstormIds.add(bestMatch.id);

      // Merge: combine sub-ideas, prefer the longer body
      const combinedSubs = deduplicateSubIdeas([
        ...bestMatch.sub_ideas,
        ...extCard.sub_ideas,
      ]);

      merged.push({
        id: extCard.id,
        title: extCard.title,
        body: extCard.body.length >= bestMatch.body.length ? extCard.body : bestMatch.body,
        sub_ideas: combinedSubs,
      });
    } else {
      merged.push(extCard);
    }
  }

  // Add unmatched brainstorm cards (unique ideas from conversation)
  for (const bsCard of brainstormCards) {
    if (!matchedBrainstormIds.has(bsCard.id)) {
      // Check it's not a near-duplicate of any merged card
      const isDup = merged.some(
        (m) => titleSimilarity(m.title, bsCard.title) >= SIMILARITY_THRESHOLD,
      );
      if (!isDup) {
        merged.push(bsCard);
      }
    }
  }

  return merged;
}
