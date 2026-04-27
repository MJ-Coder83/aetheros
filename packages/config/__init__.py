"""InkosAI Configuration Module — centralized settings management."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal


@dataclass(frozen=True)
class Settings:
    """Application settings."""

    # Database
    database_url: str = "postgresql+asyncpg://inkosai:inkosai@localhost:5432/inkosai"

    # Redis
    redis_url: str | None = None

    # JWT
    jwt_secret_key: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Plugin Sandbox
    plugin_sandbox_mode: Literal["docker", "deno", "disabled"] = "disabled"
    plugin_execution_timeout_seconds: int = 30
    plugin_memory_limit_mb: int = 512

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # CORS
    cors_origins: list[str] = None  # type: ignore

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            object.__setattr__(self, "cors_origins", ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    """Get application settings from environment variables."""
    cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")

    return Settings(
        database_url=os.environ.get("DATABASE_URL", Settings.database_url),
        redis_url=os.environ.get("REDIS_URL"),
        jwt_secret_key=os.environ.get("JWT_SECRET_KEY", Settings.jwt_secret_key),
        jwt_algorithm=os.environ.get("JWT_ALGORITHM", Settings.jwt_algorithm),
        jwt_access_token_expire_minutes=int(
            os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        ),
        jwt_refresh_token_expire_days=int(
            os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
        ),
        plugin_sandbox_mode=os.environ.get("PLUGIN_SANDBOX_MODE", "disabled"),  # type: ignore
        plugin_execution_timeout_seconds=int(
            os.environ.get("PLUGIN_EXECUTION_TIMEOUT_SECONDS", "30")
        ),
        plugin_memory_limit_mb=int(
            os.environ.get("PLUGIN_MEMORY_LIMIT_MB", "512")
        ),
        environment=os.environ.get("ENVIRONMENT", "development"),  # type: ignore
        debug=os.environ.get("DEBUG", "true").lower() == "true",
        cors_origins=cors_origins.split(","),
        rate_limit_enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
        rate_limit_requests=int(os.environ.get("RATE_LIMIT_REQUESTS", "120")),
        rate_limit_window_seconds=int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")),
    )


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    get_settings.cache_clear()
    return get_settings()
