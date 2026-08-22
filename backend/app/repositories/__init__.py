"""Postgres repository layer for Study API durable records."""


class RepositoryConflict(Exception):
    """Raised when a write violates an immutable or unique constraint.

    Attributes
    ----------
    constraint : str | None
        Database constraint name when available.
    """

    def __init__(self, message: str, *, constraint: str | None = None) -> None:
        super().__init__(message)
        self.constraint = constraint


class RepositoryNotFound(Exception):
    """Raised when a requested record does not exist."""
