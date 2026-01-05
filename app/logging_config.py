"""Logging configuration."""

from __future__ import annotations

import logging
from flask import Flask


def configure_logging(app: Flask) -> None:
    """Configure structured-ish JSON-friendly logs.

    Note: Using stdlib logging only (no extra deps).
    """

    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Reduce noisy loggers if needed
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
