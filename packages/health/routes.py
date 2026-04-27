"""Health check API routes for InkosAI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from packages.health.checks import (
    HealthChecker,
    HealthStatus,
    check_database,
    check_disk_space,
    check_plugin_sandbox,
    check_redis,
    health_checker,
)
from packages.observability.logging import get_logger

logger = get_logger(__name__)


def create_health_router() -> APIRouter:
    """Create and configure the health check router."""
    router = APIRouter(tags=["health"])

    # Register checks
    health_checker.register("database", check_database)
    health_checker.register("redis", check_redis)
    health_checker.register("plugin_sandbox", check_plugin_sandbox)
    health_checker.register("disk_space", check_disk_space)

    @router.get("/health", response_model=dict[str, Any])
    async def health() -> JSONResponse:
        """Health check endpoint - returns basic health status.

        Returns 200 if service is running, regardless of dependency health.
        """
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "inkosai-api",
                "version": "0.1.0",
            },
            status_code=status.HTTP_200_OK,
        )

    @router.get("/ready", response_model=dict[str, Any])
    async def ready() -> JSONResponse:
        """Readiness probe - returns 200 only when dependencies are healthy.

        Used by Kubernetes to determine if service is ready to receive traffic.
        """
        is_ready = await health_checker.is_ready()

        if not is_ready:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "service": "inkosai-api",
                    "checks": await health_checker.check_all(),
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return JSONResponse(
            content={
                "status": "ready",
                "service": "inkosai-api",
            },
            status_code=status.HTTP_200_OK,
        )

    @router.get("/health/detailed", response_model=dict[str, Any])
    async def health_detailed() -> JSONResponse:
        """Detailed health check with all dependency statuses.

        Returns comprehensive health information for monitoring dashboards.
        """
        results = await health_checker.check_all()
        overall_status = health_checker.get_overall_status()

        status_code = status.HTTP_200_OK
        if overall_status == HealthStatus.UNHEALTHY:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif overall_status == HealthStatus.DEGRADED:
            status_code = status.HTTP_200_OK

        response = {
            "status": overall_status.value,
            "service": "inkosai-api",
            "version": "0.1.0",
            "timestamp": "",  # Will be set by logger if needed
            "checks": {
                name: {
                    "status": result.status.value,
                    "response_time_ms": round(result.response_time_ms, 2),
                    "message": result.message,
                    "metadata": result.metadata,
                }
                for name, result in results.items()
            },
        }

        return JSONResponse(content=response, status_code=status_code)

    @router.get("/live", response_model=dict[str, str])
    async def liveness() -> JSONResponse:
        """Liveness probe - returns 200 if process is running.

        Used by Kubernetes to restart unhealthy pods.
        Kubernetes expects this to return 200 even if dependencies are failing.
        """
        return JSONResponse(
            content={
                "status": "alive",
                "service": "inkosai-api",
            },
            status_code=status.HTTP_200_OK,
        )

    return router
