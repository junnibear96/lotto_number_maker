"""Bootstrap an IAM-auth DB user in Postgres.

This script connects using an ADMIN password-based connection (one-time) to:
- create an application DB user (default: lotto_app) if missing
- grant rds_iam
- grant minimal schema privileges for table creation

Environment variables (loaded from .env and .env.local):
- PGHOST, PGPORT, PGDATABASE, PGSSLMODE
- ADMIN_DATABASE_URL (preferred) OR
- ADMIN_PGUSER (default: postgres), ADMIN_PGPASSWORD (required if ADMIN_DATABASE_URL not set)
- IAM_DB_USER (default: lotto_app)

Usage:
  C:/Users/junse/projects/lotto_number_maker/.venv/Scripts/python.exe scripts/bootstrap_iam_user.py
"""

from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def _load_env() -> None:
    load_dotenv()
    env_local = pathlib.Path(__file__).resolve().parents[1] / ".env.local"
    if env_local.exists():
        load_dotenv(dotenv_path=env_local, override=True)


def _admin_database_url() -> str:
    explicit = os.getenv("ADMIN_DATABASE_URL")
    if explicit:
        return explicit

    host = os.getenv("PGHOST")
    database = os.getenv("PGDATABASE")
    sslmode = os.getenv("PGSSLMODE", "require")

    if not host or not database:
        raise SystemExit("Missing PGHOST/PGDATABASE")

    port_raw = os.getenv("PGPORT")
    try:
        port = int(port_raw) if port_raw else 5432
    except ValueError:
        port = 5432

    user = os.getenv("ADMIN_PGUSER", "postgres")
    password = os.getenv("ADMIN_PGPASSWORD")
    if not password:
        raise SystemExit(
            "Missing ADMIN_PGPASSWORD (or set ADMIN_DATABASE_URL). "
            "This script needs a one-time admin password-based connection."
        )

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"sslmode": sslmode} if sslmode else {},
    )
    return str(url)


def main() -> int:
    _load_env()

    iam_user = os.getenv("IAM_DB_USER", "lotto_app").strip()
    if not iam_user:
        raise SystemExit("IAM_DB_USER is empty")

    engine = create_engine(_admin_database_url(), pool_pre_ping=True, future=True)

    # Create user if missing (Postgres-compatible).
    create_user_sql = text(
        """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :username) THEN
    EXECUTE format('CREATE ROLE %I WITH LOGIN', :username);
  END IF;
END $$;
"""
    )

    with engine.begin() as conn:
        conn.execute(create_user_sql, {"username": iam_user})
        conn.execute(text(f"GRANT rds_iam TO {iam_user}"))
        conn.execute(text(f"GRANT USAGE, CREATE ON SCHEMA public TO {iam_user}"))

    print(f"Bootstrapped IAM DB user: {iam_user}")
    print("Next: set PGUSER to that value and connect using IAM token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
