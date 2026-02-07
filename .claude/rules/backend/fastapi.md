---
paths:
  - "backend/app/**/*.py"
---

# FastAPI Patterns

## Dependency Injection

- Use dependency injection for database sessions
- Create reusable dependencies
- Type annotate dependencies

```python
from fastapi import Depends
from typing import Annotated

DbSession = Annotated[AsyncSession, Depends(get_db)]
```

## Pydantic Models

- Use Pydantic models for all request/response bodies
- Separate Create, Update, and Response models
- Use `from_attributes = True` for ORM compatibility

```python
class UserCreate(BaseModel):
    email: EmailStr
    name: str

class User(UserCreate):
    id: str

    class Config:
        from_attributes = True
```

## Async Endpoints

- Use `async def` for I/O-bound operations
- Await database calls
- Use `httpx.AsyncClient` for HTTP requests

## Route Organization

- Keep routes thin, logic in services/core
- Group related endpoints in routers
- Use meaningful route prefixes

## Error Handling

- Use HTTPException for client errors
- Log server errors
- Return consistent error formats
