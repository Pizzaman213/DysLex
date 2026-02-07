/**
 * Readability Score Component
 *
 * Displays Flesch-Kincaid readability metrics with an SVG ring chart.
 */

import { Badge } from '../Shared/Badge';
import { ReadabilityMetrics } from '../../utils/readabilityUtils';

interface ReadabilityScoreProps {
  metrics: ReadabilityMetrics | null;
}

export function ReadabilityScore({ metrics }: ReadabilityScoreProps) {
  if (!metrics || metrics.wordCount === 0) {
    return (
      <div
        className="readability-score"
        role="region"
        aria-label="Readability metrics"
      >
        <h3 className="readability-score-title">Readability</h3>
        <p className="readability-score-empty">
          Write some text to see readability metrics
        </p>
      </div>
    );
  }

  const getLevelBadge = () => {
    const variants: Record<string, 'success' | 'info' | 'warning'> = {
      easy: 'success',
      medium: 'info',
      advanced: 'warning',
    };
    return variants[metrics.level] || 'info';
  };

  const getLevelLabel = () => {
    const labels: Record<string, string> = {
      easy: 'Easy',
      medium: 'Medium',
      advanced: 'Advanced',
    };
    return labels[metrics.level] || metrics.level;
  };

  // SVG ring calculations
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  // Normalize score: Flesch-Kincaid grade 0-16+ mapped to 0-100%
  const scorePercent = Math.min(100, Math.max(0, (metrics.grade / 16) * 100));
  const dashOffset = circumference - (scorePercent / 100) * circumference;

  // Color based on readability level
  const ringColor =
    metrics.level === 'easy'
      ? 'var(--green)'
      : metrics.level === 'medium'
        ? 'var(--yellow)'
        : 'var(--accent)';

  return (
    <div
      className="readability-score"
      role="region"
      aria-label="Readability metrics"
    >
      <h3 className="readability-score-title">Readability</h3>

      <div className="readability-ring">
        <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">
          <circle
            className="readability-ring-bg"
            cx="60"
            cy="60"
            r={radius}
          />
          <circle
            className="readability-ring-progress"
            cx="60"
            cy="60"
            r={radius}
            style={{
              stroke: ringColor,
              strokeDasharray: circumference,
              strokeDashoffset: dashOffset,
            }}
          />
        </svg>
        <span className="readability-ring-score">
          {metrics.grade.toFixed(1)}
        </span>
      </div>
      <div className="readability-label">Flesch-Kincaid Grade</div>

      <div className="readability-score-level">
        <Badge variant={getLevelBadge()}>
          {getLevelLabel()}
        </Badge>
      </div>

      <div className="readability-score-stats">
        <div className="readability-stat">
          <span className="readability-stat-value">{metrics.wordCount}</span>
          <span className="readability-stat-label">Words</span>
        </div>
        <div className="readability-stat">
          <span className="readability-stat-value">{metrics.sentenceCount}</span>
          <span className="readability-stat-label">Sentences</span>
        </div>
        <div className="readability-stat">
          <span className="readability-stat-value">{metrics.avgSentenceLength}</span>
          <span className="readability-stat-label">Avg Length</span>
        </div>
      </div>
    </div>
  );
}
