/**
 * Words Mastered component
 * Celebrates words the user has consistently corrected
 */

import { Badge } from '../Shared/Badge';
import type { MasteredWord } from '../../types/progress';

interface WordsMasteredProps {
  words: MasteredWord[];
}

export function WordsMastered({ words }: WordsMasteredProps) {
  if (words.length === 0) {
    return (
      <section aria-label="Mastered words">
        <h2>Words Mastered</h2>
        <p className="empty-state">
          Keep writing! Words you consistently spell correctly will appear here.
        </p>
      </section>
    );
  }

  return (
    <section aria-label="Mastered words">
      <h2>🎉 {words.length} Words Mastered This Month!</h2>
      <div className="mastered-words-grid" role="list">
        {words.map((word) => (
          <div key={word.word} className="mastered-word-badge" role="listitem">
            <Badge variant="success">
              {word.word} ✓
            </Badge>
            <div className="word-metadata">
              <span className="visually-hidden">Corrected</span>
              {word.times_corrected} times
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
