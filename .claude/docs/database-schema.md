# Database Schema

## Purpose

DysLex AI uses PostgreSQL to store user data, error profiles, and correction history. The schema is designed for efficient querying of user-specific patterns and historical analysis.

## Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│    users     │────<│   error_logs     │     │error_patterns│
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id (PK)      │     │ id (PK)          │     │ id (PK)      │
│ email        │     │ user_id (FK)     │     │ name         │
│ name         │     │ original_text    │     │ description  │
│ password_hash│     │ corrected_text   │     │ category     │
│ created_at   │     │ error_type       │     │ examples     │
│ updated_at   │     │ context          │     └──────────────┘
└──────────────┘     │ confidence       │
       │             │ was_accepted     │
       │             │ created_at       │
       │             └──────────────────┘
       │
       ▼
┌──────────────────┐     ┌──────────────────┐
│  error_profiles  │     │ confusion_pairs  │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │
│ user_id (FK)     │     │ language         │
│ overall_score    │     │ word1            │
│ patterns (JSONB) │     │ word2            │
│ confusion_pairs  │     │ category         │
│ achievements     │     │ frequency        │
│ updated_at       │     └──────────────────┘
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  user_progress   │
├──────────────────┤
│ id (PK)          │
│ user_id (FK)     │
│ date             │
│ words_written    │
│ corrections_made │
│ accuracy_score   │
└──────────────────┘
```

## Tables

### users

Core user table with authentication data.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### error_profiles

Per-user adaptive profile storing patterns as JSONB.

```sql
CREATE TABLE error_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    overall_score INTEGER DEFAULT 50,
    patterns JSONB DEFAULT '[]'::jsonb,
    confusion_pairs JSONB DEFAULT '[]'::jsonb,
    achievements JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**patterns JSONB structure:**
```json
[
  {"id": "p1", "description": "b/d reversals", "mastered": false, "progress": 45},
  {"id": "p2", "description": "their/there", "mastered": true, "progress": 100}
]
```

**confusion_pairs JSONB structure:**
```json
[
  {"word1": "their", "word2": "there", "frequency": 12},
  {"word1": "your", "word2": "you're", "frequency": 8}
]
```

### error_logs

Individual correction records for analysis.

```sql
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    context TEXT,
    confidence FLOAT DEFAULT 0.0,
    was_accepted BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at);
```

### confusion_pairs

Language-specific confusion pairs (shared across users).

```sql
CREATE TABLE confusion_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language VARCHAR(10) NOT NULL,
    word1 VARCHAR(100) NOT NULL,
    word2 VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    frequency INTEGER DEFAULT 0
);

CREATE INDEX idx_confusion_pairs_language ON confusion_pairs(language);
```

### error_patterns

Predefined dyslexia error pattern categories.

```sql
CREATE TABLE error_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    examples JSONB DEFAULT '[]'::jsonb
);
```

### user_progress

Daily progress tracking for analytics.

```sql
CREATE TABLE user_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    words_written INTEGER DEFAULT 0,
    corrections_made INTEGER DEFAULT 0,
    accuracy_score FLOAT DEFAULT 0.0,
    UNIQUE(user_id, date)
);

CREATE INDEX idx_user_progress_user_date ON user_progress(user_id, date);
```

## Migrations

Managed via Alembic in the backend:

```bash
cd backend
alembic upgrade head      # Apply migrations
alembic revision --autogenerate -m "description"  # Create new migration
alembic downgrade -1      # Rollback one migration
```

## Seed Data

Initial data for error patterns and confusion pairs:

```bash
psql dyslex < database/seeds/error_types.sql
psql dyslex < database/seeds/confusion_pairs_en.sql
```

## Key Files

- `database/schema/init.sql` — Full schema
- `database/seeds/error_types.sql` — Error categories
- `database/seeds/confusion_pairs_en.sql` — English homophones
- `backend/app/db/models.py` — SQLAlchemy ORM
- `backend/alembic/` — Migration files

## SQLAlchemy Models

```python
# backend/app/db/models.py
class User(Base):
    __tablename__ = "users"
    id = mapped_column(String(36), primary_key=True)
    email = mapped_column(String(255), unique=True)
    # ...

class ErrorProfile(Base):
    __tablename__ = "error_profiles"
    id = mapped_column(String(36), primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"))
    patterns = mapped_column(JSONB, default=dict)
    # ...
```

## Queries

### Get user's top errors
```sql
SELECT original_text, corrected_text, COUNT(*) as frequency
FROM error_logs
WHERE user_id = $1
GROUP BY original_text, corrected_text
ORDER BY frequency DESC
LIMIT 20;
```

### Get improvement trend
```sql
SELECT date, accuracy_score
FROM user_progress
WHERE user_id = $1
AND date > NOW() - INTERVAL '30 days'
ORDER BY date;
```

## Status

- [x] Schema designed
- [x] Init SQL created
- [x] Seed data created
- [x] SQLAlchemy models
- [ ] Alembic migrations
- [ ] Optimization for scale
