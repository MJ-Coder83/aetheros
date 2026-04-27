"""Health check endpoint tests."""

import pytest

from packages.health.checks import CheckResult, HealthStatus


class TestHealthChecks:
    """Test individual health check functions."""

    def test_health_status_values(self) -> None:
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_check_result_creation(self) -> None:
        """Test CheckResult dataclass."""
        result = CheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            response_time_ms=1.5,
            message="Test passed"
        )
        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.metadata == {}


@pytest.mark.asyncio
class TestHealthCheckRunner:
    """Test health check runner."""

    async def test_health_checker_register(self) -> None:
        """Test that health checks can be registered."""
        from packages.health.checks import HealthChecker

        checker = HealthChecker()

        async def dummy_check() -> CheckResult:
            return CheckResult(
                name="dummy",
                status=HealthStatus.HEALTHY,
                response_time_ms=0.1
            )

        checker.register("dummy", dummy_check)
        results = await checker.check_all()

        assert "dummy" in results
        assert results["dummy"].status == HealthStatus.HEALTHY

    async def test_health_checker_overall_status_healthy(self) -> None:
        """Test overall status when all checks pass."""
        from packages.health.checks import HealthChecker

        checker = HealthChecker()

        async def healthy_check() -> CheckResult:
            return CheckResult(
                name="healthy_check",
                status=HealthStatus.HEALTHY,
                response_time_ms=0.1
            )

        checker.register("healthy", healthy_check)
        await checker.check_all()

        assert checker.get_overall_status() == HealthStatus.HEALTHY

    async def test_health_checker_overall_status_degraded(self) -> None:
        """Test overall status when check is degraded."""
        from packages.health.checks import HealthChecker

        checker = HealthChecker()

        async def degraded_check() -> CheckResult:
            return CheckResult(
                name="degraded_check",
                status=HealthStatus.DEGRADED,
                response_time_ms=0.1
            )

        checker.register("degraded", degraded_check)
        await checker.check_all()

        assert checker.get_overall_status() == HealthStatus.DEGRADED

    async def test_health_checker_overall_status_unhealthy(self) -> None:
        """Test overall status when any check is unhealthy."""
        from packages.health.checks import HealthChecker

        checker = HealthChecker()

        async def unhealthy_check() -> CheckResult:
            return CheckResult(
                name="unhealthy_check",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0.1
            )

        checker.register("unhealthy", unhealthy_check)
        await checker.check_all()

        assert checker.get_overall_status() == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
class TestDiskSpaceCheck:
    """Test disk space health check."""

    async def test_disk_space_returns_result(self) -> None:
        """Test disk space check returns a valid result."""
        from packages.health.checks import check_disk_space

        result = await check_disk_space()

        assert result.name == "disk_space"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert result.response_time_ms >= 0
        assert "free" in result.message
        assert result.metadata is not None
