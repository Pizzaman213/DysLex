/**
 * Writing Streaks & Stats component
 * Displays writing streak and lifetime statistics
 */

import { Card } from '../Shared/Card';
import type { WritingStreak, TotalStats } from '../../types/progress';

interface WritingStreaksStatsProps {
  streak: WritingStreak;
  stats: TotalStats;
}

interface StatCardProps {
  icon: string;
  value: number;
  label: string;
  unit: string;
}

function StatCard({ icon, value, label, unit }: StatCardProps) {
  return (
    <Card className="stat-card">
      <div className="stat-icon" aria-hidden="true">
        {icon}
      </div>
      <div className="stat-value" aria-label={`${value} ${unit}`}>
        {value.toLocaleString()}
      </div>
      <div className="stat-label">{label}</div>
      <span className="visually-hidden">{unit}</span>
    </Card>
  );
}

export function WritingStreaksStats({ streak, stats }: WritingStreaksStatsProps) {
  return (
    <section aria-label="Writing streaks and statistics">
      <h2>Your Progress</h2>
      <div className="writing-stats-grid">
        <StatCard
          icon="🔥"
          value={streak.current_streak}
          label="Current Streak"
          unit="days"
        />
        <StatCard
          icon="⭐"
          value={streak.longest_streak}
          label="Longest Streak"
          unit="days"
        />
        <StatCard
          icon="✍️"
          value={stats.total_words}
          label="Total Words"
          unit="words written"
        />
        <StatCard
          icon="📚"
          value={stats.total_sessions}
          label="Writing Sessions"
          unit="sessions"
        />
      </div>
    </section>
  );
}
