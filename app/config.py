"""Environment-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.engine import URL


def resolve_database_url() -> str:
    """Resolve DB connection string.

    Priority:
      1) DATABASE_URL (explicit)
      2) Build from PG* env vars (common Postgres convention)
      3) Fallback to local sqlite
    """

    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    host = os.getenv("PGHOST")
    user = os.getenv("PGUSER")
    database = os.getenv("PGDATABASE")
    port_raw = os.getenv("PGPORT")

    if host and user and database:
        password = os.getenv("PGPASSWORD")
        sslmode = os.getenv("PGSSLMODE", "require")

        try:
            port = int(port_raw) if port_raw else 5432
        except ValueError:
            port = 5432

        query = {"sslmode": sslmode} if sslmode else {}
        url = URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password,
            host=host,
            port=port,
            database=database,
            query=query,
        )
        return str(url)

    return "sqlite:///./app.db"


@dataclass(frozen=True)
class BaseConfig:
    """Base configuration shared by all environments."""

    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    DB_BACKEND: str = (
        os.getenv("DB_BACKEND")
        or ("mongo" if os.getenv("MONGODB_URI") else "sql")
    ).lower().strip()  # "sql" | "mongo"

    # SQL backend
    DATABASE_URL: str = resolve_database_url()

    # Mongo backend
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "lotto_number_maker")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


@dataclass(frozen=True)
class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG: bool = True


@dataclass(frozen=True)
class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG: bool = False


def get_config() -> type[BaseConfig]:
    """Resolve configuration class based on APP_ENV."""

    env = os.getenv("APP_ENV", "development").lower().strip()
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
