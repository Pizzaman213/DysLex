"""Database-specific exceptions for DysLex AI."""


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class RecordNotFoundError(DatabaseError):
    """Raised when a required record is not found."""

    pass


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to create a duplicate record."""

    pass


class ConstraintViolationError(DatabaseError):
    """Raised when a database constraint is violated."""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass
