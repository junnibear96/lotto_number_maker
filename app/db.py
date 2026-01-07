"""SQLAlchemy engine + session management.

Uses a session-per-request pattern.
"""

from __future__ import annotations

import os
from typing import Callable

from flask import Flask, current_app, g
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base


def get_db_backend() -> str:
    app = current_app
    return str(app.config.get("DB_BACKEND") or "sql").lower().strip()


def init_mongo(app: Flask) -> None:
    """Initialize MongoDB client and store it on app.extensions."""

    try:
        from pymongo import MongoClient
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pymongo is required for DB_BACKEND=mongo") from exc

    uri = str(app.config.get("MONGODB_URI") or "mongodb://localhost:27017")
    db_name = str(app.config.get("MONGODB_DB") or "lotto_number_maker")

    client = MongoClient(uri)
    db = client[db_name]

    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = db


def _assume_role_with_vercel_oidc(region: str) -> dict[str, str] | None:
    """Assume AWS_ROLE_ARN using VERCEL_OIDC_TOKEN if available.

    Returns a minimal credential dict compatible with boto3 clients.
    """

    token = os.getenv("VERCEL_OIDC_TOKEN")
    role_arn = os.getenv("AWS_ROLE_ARN")
    if not token or not role_arn:
        return None

    import boto3

    sts = boto3.client("sts", region_name=region)
    resp = sts.assume_role_with_web_identity(
        RoleArn=role_arn,
        RoleSessionName="vercel-oidc-rds",
        WebIdentityToken=token,
    )
    c = resp["Credentials"]
    return {
        "aws_access_key_id": c["AccessKeyId"],
        "aws_secret_access_key": c["SecretAccessKey"],
        "aws_session_token": c["SessionToken"],
    }


def _generate_rds_iam_token(*, host: str, port: int, user: str, region: str) -> str:
    """Generate an RDS IAM auth token to use as the Postgres password."""

    import boto3

    creds = _assume_role_with_vercel_oidc(region)
    if creds:
        rds = boto3.client("rds", region_name=region, **creds)
    else:
        # Falls back to whatever AWS credentials are configured locally.
        rds = boto3.client("rds", region_name=region)

    return rds.generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
        Region=region,
    )


def create_app_engine(database_url: str) -> Engine:
    url = make_url(database_url)

    # If connecting to Postgres without a static password, try IAM auth.
    if url.get_backend_name() == "postgresql" and not url.password:
        region = os.getenv("AWS_REGION")
        host = url.host
        username = url.username
        database = url.database

        if region and host and username and database:
            import psycopg2

            port = int(url.port or 5432)
            sslmode = (url.query or {}).get("sslmode") or os.getenv("PGSSLMODE") or "require"

            def _creator() -> object:
                token = _generate_rds_iam_token(
                    host=host,
                    port=port,
                    user=username,
                    region=region,
                )
                return psycopg2.connect(
                    host=host,
                    port=port,
                    user=username,
                    password=token,
                    dbname=database,
                    sslmode=sslmode,
                )

            return create_engine(
                "postgresql+psycopg2://",
                creator=_creator,
                pool_pre_ping=True,
                future=True,
            )

    return create_engine(database_url, pool_pre_ping=True, future=True)


def _create_engine(database_url: str) -> Engine:
    # Backwards-compatible alias.
    return create_app_engine(database_url)


def init_db(app: Flask) -> None:
    """Initialize database engine and per-request sessions."""

    backend = str(app.config.get("DB_BACKEND") or "sql").lower().strip()
    if backend == "mongo":
        init_mongo(app)
        return

    engine = create_app_engine(str(app.config["DATABASE_URL"]))
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

    if get_db_backend() != "sql":
        raise RuntimeError("SQLAlchemy session is not available when DB_BACKEND != sql")

    session: Session | None = getattr(g, "db", None)
    if session is None:
        raise RuntimeError("Database session not initialized")
    return session


def get_optional_session() -> Session | None:
    """Return SQLAlchemy session if configured, else None."""

    if get_db_backend() != "sql":
        return None
    return get_session()


def get_mongo_db():
    """Get the configured MongoDB database."""

    if get_db_backend() != "mongo":
        raise RuntimeError("MongoDB is not available when DB_BACKEND != mongo")

    db = current_app.extensions.get("mongo_db")
    if db is None:
        raise RuntimeError("MongoDB not initialized")
    return db
