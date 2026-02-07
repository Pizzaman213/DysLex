/**
 * Progress dashboard type definitions
 */

export interface ErrorFrequencyWeek {
  week_start: string;
  total_errors: number;
}

export interface ErrorTypeBreakdown {
  week_start: string;
  spelling: number;
  grammar: number;
  confusion: number;
  phonetic: number;
}

export interface TopError {
  original: string;
  corrected: string;
  frequency: number;
}

export interface MasteredWord {
  word: string;
  times_corrected: number;
  last_corrected: string;
}

export interface WritingStreak {
  current_streak: number;
  longest_streak: number;
  last_activity: string | null;
}

export interface TotalStats {
  total_words: number;
  total_corrections: number;
  total_sessions: number;
}

export interface ErrorTypeImprovement {
  error_type: string;
  change_percent: number;
  trend: 'improving' | 'stable' | 'needs_attention';
  sparkline_data: number[];
}

export interface ProgressDashboardResponse {
  error_frequency: ErrorFrequencyWeek[];
  error_breakdown: ErrorTypeBreakdown[];
  top_errors: TopError[];
  mastered_words: MasteredWord[];
  writing_streak: WritingStreak;
  total_stats: TotalStats;
  improvements: ErrorTypeImprovement[];
}
