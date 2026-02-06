"""User models."""

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: EmailStr | None = None
    name: str | None = None


class User(UserBase):
    """User response schema."""

    id: str

    class Config:
        from_attributes = True
