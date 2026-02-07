"""Authentication endpoints — register, login, refresh."""

import uuid

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator

from app.api.dependencies import (
    DbSession,
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.db.models import User as UserORM
from app.db.repositories.user_repo import create_user, get_user_by_email, get_user_by_id
from app.middleware.rate_limiter import limiter
from app.models.envelope import ApiError, error_response, success_response

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    token: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: DbSession) -> dict:
    """Create a new user account and return a JWT."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        return error_response(
            [ApiError(code="EMAIL_EXISTS", message="Email already registered")],
            status_code=409,
        )

    user = UserORM(
        id=str(uuid.uuid4()),
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    user = await create_user(db, user)

    token = create_access_token(user.id, user.email)
    return success_response(
        AuthToken(access_token=token, user_id=user.id).model_dump(),
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, db: DbSession) -> dict:
    """Validate credentials and return a JWT."""
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)
    return success_response(
        AuthToken(access_token=token, user_id=user.id).model_dump(),
    )


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: DbSession) -> dict:
    """Refresh an expiring token."""
    payload = verify_token(body.token)
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_token = create_access_token(user.id, user.email)
    return success_response(
        AuthToken(access_token=new_token, user_id=user.id).model_dump(),
    )
