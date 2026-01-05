"""Helpers for consistent JSON response schema."""

from __future__ import annotations

from typing import Any

from flask import Response, jsonify


def ok(data: Any, status_code: int = 200) -> Response:
    """Success response."""

    return jsonify({"success": True, "data": data, "error": None}), status_code


def fail(code: str, message: str, status_code: int, details: Any | None = None) -> Response:
    """Error response."""

    return (
        jsonify(
            {
                "success": False,
                "data": None,
                "error": {"code": code, "message": message, "details": details},
            }
        ),
        status_code,
    )
