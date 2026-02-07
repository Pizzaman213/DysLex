"""Generic API response envelope."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    """Structured error detail."""

    code: str
    message: str
    field: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard response envelope wrapping all API responses."""

    status: str = "success"
    data: T | None = None
    errors: list[ApiError] = []
    meta: dict = {}


def success_response(data: object, **meta: object) -> dict:
    """Build a success envelope dict."""
    return {
        "status": "success",
        "data": data,
        "errors": [],
        "meta": meta,
    }


def error_response(errors: list[ApiError], status_code: int = 400) -> dict:
    """Build an error envelope dict."""
    return {
        "status": "error",
        "data": None,
        "errors": [e.model_dump() for e in errors],
        "meta": {},
    }
