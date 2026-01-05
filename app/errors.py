"""Custom exceptions for centralized error handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    """Base application error."""

    code: str
    message: str
    status_code: int
    details: Any | None = None


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Not found", details: Any | None = None) -> None:
        super().__init__(code="not_found", message=message, status_code=404, details=details)


class ValidationError(AppError):
    """Input validation error."""

    def __init__(self, message: str = "Validation error", details: Any | None = None) -> None:
        super().__init__(code="validation_error", message=message, status_code=400, details=details)


class ConflictError(AppError):
    """Conflict (e.g., unique constraint)."""

    def __init__(self, message: str = "Conflict", details: Any | None = None) -> None:
        super().__init__(code="conflict", message=message, status_code=409, details=details)
