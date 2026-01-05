"""Health check routes."""

from __future__ import annotations

from flask import Blueprint

from app.utils.responses import ok

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Health check endpoint."""

    return ok({"status": "ok"})
