# Database Schema

## Purpose

PostgreSQL stores user data, error profiles, documents, and correction history. Schema is managed entirely via **Alembic migrations** (no raw SQL init files).

## ORM Models

`backend/app/db/models.py` — SQLAlchemy 2.0 with async support:

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | UUID PK, email (unique), name, password_hash |
| `UserSettings` | `user_settings` | 29 columns: theme, fonts, accessibility, voice, corrections |
| `ErrorLog` | `error_logs` | Raw correction records (original, corrected, type, confidence, source) |
| `UserErrorPattern` | `user_error_patterns` | Per-user misspelling→correction frequency (unique on user+misspelling+correction) |
| `UserConfusionPair` | `user_confusion_pairs` | Word confusion tracking (unique on user+word_a+word_b) |
| `PersonalDictionary` | `personal_dictionary` | Words to never flag (unique on user+word) |
| `ProgressSnapshot` | `progress_snapshots` | Weekly aggregated stats (unique on user+week_start) |
| `Document` | `documents` | User documents with content, title, mode |
| `Folder` | `folders` | Document organization |
| `PasskeyCredential` | `passkey_credentials` | WebAuthn credentials |

All models use UUID string primary keys. Relationships with `CASCADE` delete.

## Migrations

8 Alembic migrations in `backend/alembic/versions/`:

| Migration | Purpose |
|-----------|---------|
| 001 | Add error profile tables (patterns, confusion pairs, dictionary, logs) |
| 002 | Add user_settings table |
| 003 | Deprecate old error_profiles JSONB table |
| 004 | Add composite indexes for query performance |
| 005 | Add documents and folders |
| 006 | Add passkey_credentials for WebAuthn |
| 007 | Add missing settings columns |
| 008 | Add error_logs created_at index |

```bash
cd backend
alembic upgrade head         # Apply all migrations
alembic revision --autogenerate -m "description"  # Create new
alembic downgrade -1         # Rollback one
```

## Repository Pattern

All database access goes through repository modules:

| Repository | File | Key Operations |
|-----------|------|---------------|
| User | `backend/app/db/repositories/user_repo.py` | CRUD, lookup by email/id |
| Error Patterns | `backend/app/db/repositories/user_error_pattern_repo.py` | Upsert, top/mastered patterns |
| Progress | `backend/app/db/repositories/progress_repo.py` | Weekly stats, streaks, trends |

## Key Files

| File | Role |
|------|------|
| `backend/app/db/models.py` | All SQLAlchemy ORM models |
| `backend/alembic/versions/` | Migration files (001-008) |
| `backend/alembic/env.py` | Alembic configuration |
| `backend/app/db/repositories/` | Repository modules |
| `backend/app/api/dependencies.py` | `get_db()` session dependency |

## Integration Points

- [Error Profile](../core/error-profile-system.md): Reads from pattern/confusion/dictionary tables
- [Adaptive Loop](../core/adaptive-learning-loop.md): Writes to error_logs and patterns
- [Scheduler](background-scheduler.md): Runs cleanup and aggregation jobs

## Status

- [x] Full normalized schema (8 migrations)
- [x] SQLAlchemy 2.0 async ORM
- [x] Repository pattern for all queries
- [x] Composite indexes for performance
- [ ] Database optimization for scale
