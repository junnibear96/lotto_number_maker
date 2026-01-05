"""SQLAlchemy engine + session management.

Uses a session-per-request pattern.
"""

from __future__ import annotations

from typing import Callable

from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base


def _create_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


def init_db(app: Flask) -> None:
    """Initialize database engine and per-request sessions."""

    engine = _create_engine(str(app.config["DATABASE_URL"]))
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    # Create tables for the example (production would use migrations).
    Base.metadata.create_all(bind=engine)

    app.extensions["engine"] = engine
    app.extensions["session_factory"] = session_factory

    @app.before_request
    def _open_session() -> None:
        g.db = session_factory()  # type: ignore[attr-defined]

    @app.teardown_request
    def _close_session(exc: BaseException | None) -> None:
        session: Session | None = getattr(g, "db", None)
        if session is None:
            return

        try:
            if exc is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()


def get_session() -> Session:
    """Get the current request's SQLAlchemy session."""

    session: Session | None = getattr(g, "db", None)
    if session is None:
        raise RuntimeError("Database session not initialized")
    return session
