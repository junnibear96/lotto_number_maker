"""Create database tables in the configured database.

Reads DATABASE_URL from .env / environment and creates all registered ORM tables.

Usage:
  ./.venv/Scripts/python scripts/create_tables.py
"""

from __future__ import annotations

import pathlib
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.base import Base
from app.config import resolve_database_url
from app.db import create_app_engine

# Import models so they register with Base.metadata
from app import models  # noqa: F401


def main() -> int:
    """Create all ORM tables in the target database."""

    load_dotenv()
    env_local = PROJECT_ROOT / ".env.local"
    if env_local.exists():
        load_dotenv(dotenv_path=env_local, override=True)

    database_url = resolve_database_url()

    engine = create_app_engine(database_url)
    Base.metadata.create_all(bind=engine)

    # create_all() does not add indexes/constraints to existing tables.
    # For PostgreSQL, apply them idempotently.
    if engine.dialect.name == "postgresql":
        ddl = [
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lotto_numbers_draw_no ON lotto_numbers (draw_no)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number1 ON lotto_numbers (number1)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number2 ON lotto_numbers (number2)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number3 ON lotto_numbers (number3)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number4 ON lotto_numbers (number4)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number5 ON lotto_numbers (number5)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_number6 ON lotto_numbers (number6)",
            "CREATE INDEX IF NOT EXISTS ix_lotto_numbers_bonus_number ON lotto_numbers (bonus_number)",
        ]
        with engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))

    print("Tables created (or already exist).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
