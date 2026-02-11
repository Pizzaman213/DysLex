# Error Profile System

## Purpose

Per-user database tracking individual dyslexic error patterns, enabling personalized corrections that improve over time. Users never interact with it directly.

## Data Model (Normalized Tables)

The error profile uses normalized PostgreSQL tables (not a single JSONB blob):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `user_error_patterns` | Per-user misspelling→correction frequency | `misspelling`, `correction`, `frequency`, `error_type`, `first_seen`, `last_seen`, `improving` |
| `user_confusion_pairs` | Frequently confused word pairs | `word_a`, `word_b`, `count` |
| `personal_dictionary` | Words to never flag | `word`, `added_at` |
| `error_logs` | Raw correction records | `original_text`, `corrected_text`, `error_type`, `confidence`, `was_accepted`, `source` |
| `progress_snapshots` | Weekly aggregated stats | `week_start`, `total_errors`, `breakdown` (JSONB), `top_errors` (JSONB) |

All tables use unique constraints on `(user_id, ...)` for upsert operations. Managed via Alembic migrations.

## ErrorProfileService

Central service in `backend/app/core/error_profile.py`:

| Method | Purpose |
|--------|---------|
| `get_full_profile(user_id, db)` | Assembles complete profile from 3 queries, Redis-cached 10 min |
| `build_llm_context(user_id, db)` | Builds `LLMContext` for every LLM prompt with enrichment data |
| `log_error(user_id, db, ...)` | Logs raw error + upserts pattern table |
| `detect_improvement(user_id, db)` | Checks for improving patterns |
| `generate_weekly_snapshot(user_id, db)` | Aggregates weekly progress data |

### LLMContext (Prompt Enrichment)

`build_llm_context()` returns an `LLMContext` Pydantic model containing:
- `top_errors` — 20 most frequent misspellings with corrections
- `error_types` — Percentage breakdown by error category
- `confusion_pairs` — Top 10 confused word pairs
- `grammar_patterns` — Frequent grammar issues
- `writing_level` — Estimated level
- `personal_dictionary` — Words to skip
- `mastered_words` — Words no longer flagged (14+ days unseen)
- `improvement_trends` — Improving vs needs-attention patterns
- `writing_streak` / `total_stats` — Session metrics

## Key Files

| File | Role |
|------|------|
| `backend/app/core/error_profile.py` | `ErrorProfileService` — central service |
| `backend/app/db/models.py` | ORM models for all profile tables |
| `backend/app/db/repositories/user_error_pattern_repo.py` | Pattern CRUD with upsert |
| `backend/app/db/repositories/progress_repo.py` | Dashboard queries (trends, streaks, stats) |
| `backend/app/models/error_log.py` | `LLMContext` Pydantic model |
| `backend/app/core/prompt_builder.py` | Uses `LLMContext` to build prompts |

## Integration Points

- [Adaptive Loop](adaptive-learning-loop.md): Feeds corrections into profile via `log_error()`
- [LLM Orchestrator](../backend/llm-orchestrator.md): Uses `build_llm_context()` for prompts
- [Coach](../backend/llm-orchestrator.md): Coach prompts use profile for personalization
- [Scheduler](../backend/background-scheduler.md): Runs improvement detection and cleanup
- [Redis](../backend/redis-caching-layer.md): Caches assembled profiles (10 min TTL)

## Status

- [x] Normalized table schema (patterns, confusion pairs, dictionary)
- [x] ErrorProfileService with Redis caching
- [x] LLMContext builder for prompt enrichment
- [x] Repository pattern for all queries
- [x] Alembic migrations (001-008)
- [x] Weekly progress snapshots
- [ ] Profile export/delete for user privacy
- [ ] Admin analytics (anonymized)
