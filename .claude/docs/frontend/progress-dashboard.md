# Progress Dashboard

## Purpose

Shows users their improvement over time. Designed to motivate — never to shame. Users discover their progress when they choose to look.

## Metrics (Always Positive Framing)

- **Writing Strength** score (0-100, labels: Getting Started → Excellent)
- **Patterns mastered** — Words the user no longer misspells (14+ days unseen)
- **Writing streak** — Consecutive days with activity
- **Weekly stats** — Words written, improvements made

## Backend Data Sources

`backend/app/db/repositories/progress_repo.py`:

| Function | Purpose |
|----------|---------|
| `get_error_frequency_by_week()` | Weekly error counts (excludes self-corrections) |
| `get_error_breakdown_by_type()` | Error counts by type per week |
| `get_improvement_by_error_type()` | Trend analysis (first half vs second half) |
| `get_writing_streak()` | Current/longest streaks |
| `get_total_stats()` | Lifetime word/correction/session counts |
| `get_top_errors()` | Most frequent error pairs |

Trend algorithm: compares first/second half of period, classifies as `improving`/`needs_attention`/`stable` based on +/-10% threshold.

## Key Files

| File | Role |
|------|------|
| `backend/app/db/repositories/progress_repo.py` | Dashboard queries |
| `backend/app/db/models.py` | `ProgressSnapshot` model |
| `backend/app/core/error_profile.py` | `generate_weekly_snapshot()` |

## Status

- [x] Backend queries for all metrics
- [x] Weekly progress snapshot generation (scheduler job)
- [x] Writing streak calculation
- [x] Trend analysis algorithm
- [ ] Frontend dashboard component
- [ ] Achievement/gamification system
- [ ] Historical chart visualization
