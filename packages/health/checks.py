"""Health check implementations for InkosAI services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import text

from packages.observability.logging import get_logger
from packages.observability.metrics import (
    db_connections_active,
    health_check_duration,
    redis_connections_active,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class HealthStatus(StrEnum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str = ""
    metadata: dict = None  # type: ignore

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class HealthChecker:
    """Comprehensive health checker for InkosAI."""

    def __init__(self) -> None:
        self._checks: dict[str, callable] = {}
        self._results: dict[str, CheckResult] = {}

    def register(self, name: str, check_fn: callable) -> None:
        """Register a health check."""
        self._checks[name] = check_fn

    async def check_all(self) -> dict[str, CheckResult]:
        """Run all registered health checks."""
        results = {}
        for name, check_fn in self._checks.items():
            try:
                start = datetime.now(UTC)
                result = await check_fn()
                duration = (datetime.now(UTC) - start).total_seconds()
                result.response_time_ms = duration * 1000
                results[name] = result
                health_check_duration.labels(check_type=name).observe(duration)
            except Exception as e:
                results[name] = CheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Check failed with exception: {e}",
                )
                logger.error("Health check failed", check=name, error=str(e))
        self._results = results
        return results

    def get_overall_status(self) -> HealthStatus:
        """Determine overall health status from all checks."""
        if not self._results:
            return HealthStatus.UNHEALTHY

        statuses = [r.status for r in self._results.values()]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    async def is_ready(self) -> bool:
        """Check if service is ready to accept traffic."""
        if not self._checks:
            return True
        await self.check_all()
        critical_checks = ["database", "redis"]
        for check_name in critical_checks:
            result = self._results.get(check_name)
            if result and result.status == HealthStatus.UNHEALTHY:
                return False
        return True


async def check_database(db: AsyncSession | None = None) -> CheckResult:
    """Check database connectivity using existing session."""
    from services.api.database import async_session

    start = datetime.now(UTC)
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            await result.scalar()
        duration = (datetime.now(UTC) - start).total_seconds()
        db_connections_active.set(1)  # Simplified - actual count would come from pool
        return CheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            response_time_ms=duration * 1000,
            message="Database connection successful",
        )
    except Exception as e:
        db_connections_active.set(0)
        return CheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Database connection failed: {e}",
        )


async def check_redis() -> CheckResult:
    """Check Redis connectivity."""
    import redis.asyncio as redis

    from packages.config import get_settings

    start = datetime.now(UTC)
    settings = get_settings()

    if not settings.redis_url:
        return CheckResult(
            name="redis",
            status=HealthStatus.DEGRADED,
            response_time_ms=0,
            message="Redis URL not configured",
        )

    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.close()
        duration = (datetime.now(UTC) - start).total_seconds()
        redis_connections_active.set(1)
        return CheckResult(
            name="redis",
            status=HealthStatus.HEALTHY,
            response_time_ms=duration * 1000,
            message="Redis connection successful",
        )
    except Exception as e:
        redis_connections_active.set(0)
        return CheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Redis connection failed: {e}",
        )


async def check_plugin_sandbox() -> CheckResult:
    """Check plugin sandbox availability."""
    from packages.config import get_settings

    settings = get_settings()
    if settings.plugin_sandbox_mode == "disabled":
        return CheckResult(
            name="plugin_sandbox",
            status=HealthStatus.HEALTHY,
            response_time_ms=0,
            message="Plugin sandbox is disabled (expected in some configurations)",
        )

    start = datetime.now(UTC)
    try:
        # Simple check - verify the sandbox directory exists and is writable
        import os

        sandbox_dir = os.environ.get("SANDBOX_DIR", "/tmp/sandbox")
        if not os.path.exists(sandbox_dir):
            os.makedirs(sandbox_dir, exist_ok=True)

        # Test write
        test_file = os.path.join(sandbox_dir, ".health_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)

        duration = (datetime.now(UTC) - start).total_seconds()
        return CheckResult(
            name="plugin_sandbox",
            status=HealthStatus.HEALTHY,
            response_time_ms=duration * 1000,
            message="Plugin sandbox is available",
        )
    except Exception as e:
        return CheckResult(
            name="plugin_sandbox",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Plugin sandbox check failed: {e}",
        )


async def check_disk_space() -> CheckResult:
    """Check available disk space."""
    import shutil

    start = datetime.now(UTC)
    try:
        stat = shutil.disk_usage("/tmp")
        free_gb = stat.free / (1024 ** 3)
        total_gb = stat.total / (1024 ** 3)
        used_percent = (stat.used / stat.total) * 100

        duration = (datetime.now(UTC) - start).total_seconds()

        if used_percent > 95:
            status = HealthStatus.UNHEALTHY
        elif used_percent > 80:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return CheckResult(
            name="disk_space",
            status=status,
            response_time_ms=duration * 1000,
            message=f"Disk usage: {used_percent:.1f}% ({free_gb:.1f}GB free of {total_gb:.1f}GB)",
            metadata={"free_gb": free_gb, "used_percent": used_percent},
        )
    except Exception as e:
        return CheckResult(
            name="disk_space",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            message=f"Disk space check failed: {e}",
        )


# Global health checker instance
health_checker = HealthChecker()
