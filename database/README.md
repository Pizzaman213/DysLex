# Database

PostgreSQL database schemas and seed data for DysLex AI.

## Schema

The initial schema is defined in `schema/init.sql` and managed via Alembic migrations in the backend.

## Seed Data

- `seeds/error_types.sql` - Predefined error type categories
- `seeds/confusion_pairs_en.sql` - English confusion pairs

## Setup

```bash
# Create database
createdb dyslex

# Run initial schema
psql dyslex < schema/init.sql

# Run seeds
psql dyslex < seeds/error_types.sql
psql dyslex < seeds/confusion_pairs_en.sql
```

## Migrations

Database migrations are managed via Alembic in the backend:

```bash
cd backend
alembic upgrade head
```
