# Database Layer Architecture

## Overview

The DysLex AI database layer provides the data persistence foundation for the adaptive learning system. It uses PostgreSQL 15 with async SQLAlchemy 2.0 and follows the repository pattern for clean separation of data access logic.

## Directory Structure

```
backend/app/db/
├── models.py           # SQLAlchemy ORM models
├── database.py         # Database connection and session factory
├── exceptions.py       # Custom database exceptions
├── repositories/       # Repository modules (one per table)
│   ├── user_repo.py
│   ├── settings_repo.py
│   ├── error_log_repo.py
│   ├── user_error_pattern_repo.py
│   ├── user_confusion_pair_repo.py
│   ├── personal_dictionary_repo.py
│   ├── progress_snapshot_repo.py
│   ├── progress_repo.py
│   ├── error_pattern_repo.py
│   └── confusion_pair_repo.py
└── README.md           # This file
```

## Database Tables

### Core Tables

**users** — User accounts
- Primary key: UUID
- Unique constraint: email
- Cascade deletes to all related tables

**user_settings** — Per-user preferences
- Font, theme, accessibility settings
- Privacy settings (data collection, cloud sync)
- 1:1 relationship with users

**error_logs** — Raw error events for passive learning
- Captures: original text, corrected text, error type, context
- Source field: 'passive', 'quick_model', 'deep_model', 'self_corrected'
- Indexed on: user_id, created_at, source

**user_error_patterns** — Aggregated misspelling frequency map
- Unique constraint: (user_id, misspelling, correction)
- Tracks frequency, first_seen, last_seen, improving flag
- Powers the Adaptive Brain (Error Profile Model 1)

**user_confusion_pairs** — Homophone/confusion tracking
- Alphabetically normalized (word_a < word_b)
- Unique constraint: (user_id, word_a, word_b)
- Tracks confusion_count, last_confused_at

**personal_dictionary** — User-curated word whitelist
- Words the user added to never flag
- Source: 'manual' (user-added) or 'auto' (system-detected)

**progress_snapshots** — Weekly aggregated statistics
- One snapshot per user per week (Monday week_start)
- JSONB fields: error_type_breakdown, top_errors
- Powers the Progress Dashboard (Module 6)

### Reference Tables

**error_patterns** — Known dyslexia error pattern definitions
- Seed data: Letter reversals, phonetic substitutions, etc.
- Category-based organization

**confusion_pairs** — Language-specific confusion references
- Seed data: their/there/they're, effect/affect, etc.
- Language-scoped (e.g., language='en')

## Repository Pattern

### Why Repositories?

Repositories encapsulate all database access logic, providing:
- Clean separation between data access and business logic
- Consistent async/await patterns
- Type-safe interfaces with proper error handling
- Easy testability (mock repositories, not raw SQL)

### Function-Based Pattern

This codebase uses **function-based repositories** (modules of async functions) rather than class-based repositories.

**Example**:
```python
# user_repo.py
async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        raise ConnectionError("Database connection failed") from e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise DatabaseError(f"Failed to get user: {e}") from e
```

### Transaction Boundaries

**Critical Rule**: Repositories use `flush()`, never `commit()`.

```python
# CORRECT ✅
db.add(user)
await db.flush()      # Inserts without committing
await db.refresh(user)
return user

# WRONG ❌
db.add(user)
await db.commit()     # Breaks transaction boundaries
```

**Why**: FastAPI's dependency injection provides `get_session()` which manages the transaction lifecycle. Committing inside a repository breaks this pattern and prevents proper rollback on errors.

## Error Handling

All repository functions use comprehensive error handling:

```python
try:
    # Database operation
except IntegrityError as e:
    logger.error(f"Integrity error: {e}")
    raise DuplicateRecordError("Record already exists") from e
except OperationalError as e:
    logger.error(f"Connection error: {e}")
    raise ConnectionError("Database connection failed") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise DatabaseError("Operation failed") from e
```

**Custom Exceptions** (defined in `exceptions.py`):
- `DatabaseError` — Base exception for all database errors
- `RecordNotFoundError` — Required record doesn't exist
- `DuplicateRecordError` — Unique constraint violation
- `ConstraintViolationError` — Foreign key or check constraint violation
- `ConnectionError` — Database connection failure

## Migrations (Alembic)

### Running Migrations

```bash
cd backend
alembic upgrade head      # Apply all pending migrations
alembic downgrade -1      # Rollback one migration
alembic history           # Show migration history
alembic current           # Show current revision
```

### Creating Migrations

```bash
alembic revision --autogenerate -m "Add new table"
```

**Important**: Always review autogenerated migrations before applying. Alembic may miss:
- Index changes
- Constraint modifications
- Custom SQL (triggers, functions)

### Migration History

- **001**: Add normalized error profile tables (user_error_patterns, user_confusion_pairs, personal_dictionary, progress_snapshots)
- **002**: Add user_settings table
- **003**: Deprecate legacy error_profiles JSONB table

## Testing

### Test Database Setup

Tests use an in-memory SQLite database for speed:

```python
# conftest.py
@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # ... yield session
```

### Running Tests

```bash
# All repository tests
pytest backend/tests/test_repositories.py -v

# Specific repository
pytest backend/tests/test_repositories.py::test_create_user -v

# Error handling tests
pytest backend/tests/test_repository_errors.py -v

# Privacy/GDPR tests
pytest backend/tests/test_privacy_endpoints.py -v
```

## Adding New Tables

1. **Define ORM Model** in `models.py`:
```python
class NewTable(Base):
    __tablename__ = "new_table"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # ... other columns
```

2. **Create Migration**:
```bash
alembic revision --autogenerate -m "Add new_table"
```

3. **Create Repository** in `repositories/new_table_repo.py`:
```python
async def get_by_user(db: AsyncSession, user_id: str):
    # ... implementation with error handling
```

4. **Add Tests** in `tests/test_repositories.py`

5. **Update CASCADE Delete**: Ensure foreign keys use `ondelete="CASCADE"` for GDPR compliance

## Privacy & GDPR Compliance

### Data Export

The `/api/users/{user_id}/export` endpoint returns all user data in JSON format:
- User profile
- Settings
- Error logs (last 10,000)
- Error patterns
- Confusion pairs
- Personal dictionary
- Progress snapshots (last 2 years)

### Data Deletion

The `/api/users/{user_id}` DELETE endpoint:
1. Deletes the user record
2. CASCADE deletes propagate to all related tables:
   - UserSettings
   - ErrorLog
   - UserErrorPattern
   - UserConfusionPair
   - PersonalDictionary
   - ProgressSnapshot

**No orphaned data remains after user deletion.**

## Performance Considerations

### Indexes

All critical queries are covered by indexes in `init.sql`:
- `idx_error_logs_user_id` — User-scoped queries
- `idx_user_error_patterns_user_freq` — Top patterns by frequency
- `idx_progress_snapshots_user_week` — Weekly snapshot retrieval

### Query Optimization

For large datasets:
- Use `limit` and `offset` for pagination
- Add date filtering to error_logs queries
- Consider eager loading with `selectinload()` for relationships

### Connection Pooling

SQLAlchemy default pool settings:
- Pool size: 5
- Max overflow: 10
- Pool pre-ping: Enabled (validates connections before use)

Tune for production load in `database.py` if needed.

## Common Patterns

### Upsert (Insert or Update)

```python
async def upsert_pattern(db, user_id, misspelling, correction):
    stmt = select(UserErrorPattern).where(...)
    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()

    if pattern:
        pattern.frequency += 1
        pattern.last_seen = datetime.utcnow()
    else:
        pattern = UserErrorPattern(...)
        db.add(pattern)

    await db.flush()
    await db.refresh(pattern)
    return pattern
```

### Aggregation Queries

```python
async def get_error_type_counts(db, user_id):
    stmt = (
        select(
            UserErrorPattern.error_type,
            func.count(UserErrorPattern.id).label("count")
        )
        .where(UserErrorPattern.user_id == user_id)
        .group_by(UserErrorPattern.error_type)
    )
    result = await db.execute(stmt)
    return {row.error_type: row.count for row in result}
```

### Cleanup/Archival

```python
async def archive_old_logs(db, user_id, days=365):
    """Delete logs older than N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        delete(ErrorLog).where(
            ErrorLog.user_id == user_id,
            ErrorLog.created_at < cutoff,
        )
    )
    await db.flush()
    return result.rowcount
```

## Troubleshooting

### "Database is locked" (SQLite)
- Only occurs in tests. Use `check_same_thread=False` in connection string.

### "Relationship loop detected"
- Check for circular imports in models.py
- Use string references for forward relationships

### "Session is already closed"
- Using `commit()` in repository? Change to `flush()`
- Not yielding session in dependency? Check `get_session()` context manager

### Migration conflicts
- Multiple developers creating migrations? Resolve with `alembic merge`
- Autogenerate missed changes? Manually edit migration file

## Data Retention Policies

For GDPR compliance and performance:

- **Error logs**: Archive logs older than 1 year using `archive_old_logs()`
- **Progress snapshots**: Keep last 2 years only using `delete_snapshots_before_date()`
- **User deletion**: All related data is cascade deleted automatically

## Repository Function Reference

### user_repo.py
- `get_user_by_id(db, user_id)` — Get user by ID
- `get_user_by_email(db, email)` — Get user by email
- `create_user(db, user)` — Create new user
- `update_user(db, user)` — Update user
- `delete_user(db, user)` — Delete user (cascade)

### error_log_repo.py
- `create_error_log(db, user_id, original, corrected, error_type, ...)` — Log error
- `get_error_logs_by_user(db, user_id, limit)` — Get user's error logs
- `get_error_count_by_period(db, user_id, days)` — Count errors in period
- `get_recent_errors_for_words(db, user_id, words, days)` — Filter by words
- `delete_logs_before_date(db, user_id, cutoff_date)` — Cleanup old logs
- `archive_old_logs(db, user_id, days)` — Archive logs older than N days

### user_error_pattern_repo.py
- `get_top_patterns(db, user_id, limit)` — Get most frequent patterns
- `upsert_pattern(db, user_id, misspelling, correction, error_type)` — Insert/update pattern
- `get_error_type_counts(db, user_id)` — Aggregate by error type
- `get_mastered_patterns(db, user_id, days_threshold)` — Patterns not seen recently
- `mark_pattern_improving(db, pattern_id, improving)` — Set improving flag
- `get_pattern_count(db, user_id)` — Total distinct patterns

### user_confusion_pair_repo.py
- `get_pairs_for_user(db, user_id, limit)` — Get confusion pairs
- `upsert_confusion_pair(db, user_id, word_a, word_b)` — Insert/update pair

### personal_dictionary_repo.py
- `get_dictionary(db, user_id)` — Get all dictionary entries
- `check_word(db, user_id, word)` — Check if word exists
- `add_word(db, user_id, word, source)` — Add word to dictionary
- `remove_word(db, user_id, word)` — Remove word from dictionary

### progress_snapshot_repo.py
- `get_snapshots(db, user_id, weeks)` — Get weekly snapshots
- `upsert_snapshot(db, user_id, week_start, ...)` — Insert/update snapshot
- `delete_snapshots_before_date(db, user_id, cutoff_date)` — Cleanup old snapshots

### progress_repo.py
- `get_error_frequency_by_week(db, user_id, weeks)` — Weekly error counts
- `get_error_breakdown_by_type(db, user_id, weeks)` — Errors by type per week
- `get_top_errors(db, user_id, limit, weeks)` — Most frequent error pairs
- `get_mastered_words(db, user_id, weeks)` — Words with 3+ self-corrections
- `get_writing_streak(db, user_id)` — Current and longest streak
- `get_total_stats(db, user_id)` — Lifetime statistics
- `get_improvement_by_error_type(db, user_id, weeks)` — Improvement trends

### error_pattern_repo.py (Reference Data)
- `get_all_patterns(db)` — Get all error patterns
- `get_pattern_by_id(db, pattern_id)` — Get pattern by ID
- `get_patterns_by_category(db, category)` — Filter by category
- `create_pattern(db, pattern)` — Create new pattern

### confusion_pair_repo.py (Reference Data)
- `get_pairs_by_language(db, language)` — Get pairs for language
- `get_pair_containing_word(db, word, language)` — Find pairs with word
- `increment_pair_frequency(db, pair_id)` — Increment frequency counter

---

**For questions or issues, see `/docs/MODULE_7_DATABASE_LAYER.md` or check existing tests for examples.**
