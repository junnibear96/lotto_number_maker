"""Centralized error handlers."""

from __future__ import annotations

import logging

from flask import Flask
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.errors import AppError, ConflictError, ValidationError
from app.utils.responses import fail

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""

    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError):
        return fail(exc.code, exc.message, exc.status_code, exc.details)

    @app.errorhandler(MarshmallowValidationError)
    def _handle_schema_error(exc: MarshmallowValidationError):
        # exc.messages is a dict of field -> list[str]
        wrapped = ValidationError(details=exc.messages)
        return fail(wrapped.code, wrapped.message, wrapped.status_code, wrapped.details)

    @app.errorhandler(IntegrityError)
    def _handle_integrity_error(exc: IntegrityError):
        logger.info("Integrity error", exc_info=exc)
        wrapped = ConflictError(details=str(exc.orig) if exc.orig else str(exc))
        return fail(wrapped.code, wrapped.message, wrapped.status_code, wrapped.details)

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        # Examples: 404 Not Found for /favicon.ico.
        status = int(getattr(exc, "code", 500) or 500)
        if status == 404:
            return fail("not_found", "Not found", 404)

        return fail(
            "http_error",
            getattr(exc, "description", "HTTP error"),
            status,
            details={"name": getattr(exc, "name", "HTTPException")},
        )

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        logger.exception("Unhandled exception")
        return fail("internal_error", "Internal server error", 500)
