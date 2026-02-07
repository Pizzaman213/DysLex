---
paths:
  - "backend/app/db/**/*.py"
---

# Database Access Patterns

## Repository Pattern

- Use repositories for database access
- Keep SQL logic in repositories
- Return domain objects, not ORM objects

```python
async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

## Async Sessions

- Always use async sessions
- Use context managers for transactions
- Handle rollback on exceptions

```python
async with async_session() as session:
    try:
        # operations
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

## Queries

- Use SQLAlchemy 2.0 style queries
- Avoid N+1 queries
- Use `selectinload` for relationships

## Migrations

- Use Alembic for migrations
- Write reversible migrations
- Test migrations before deploying
