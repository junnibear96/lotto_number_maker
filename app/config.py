"""Environment-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseConfig:
    """Base configuration shared by all environments."""

    APP_ENV: str = os.getenv("APP_ENV", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
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
