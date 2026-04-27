"""Smoke tests for critical application paths."""

import pytest
from unittest.mock import AsyncMock, patch


class TestCriticalPathsSmoke:
    """Smoke tests without external dependencies."""

    def test_imports_work(self) -> None:
        """Verify all critical modules import."""
        from packages.health import create_health_router
        from packages.observability import get_logger
        from packages.observability.metrics import (
            http_requests_total,
            record_http_request,
        )

        assert create_health_router is not None
        assert get_logger is not None
        assert http_requests_total is not None

    def test_auth_models_import(self) -> None:
        """Verify auth models import."""
        from packages.auth import (
            User,
            UserRole,
            TokenResponse,
            LoginRequest,
            RegisterRequest,
        )

        user = User(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            role=UserRole.VIEWER,
        )
        assert user.username == "testuser"

    def test_config_import(self) -> None:
        """Verify config imports."""
        from packages.config import Settings, get_settings

        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, 'database_url')


class TestHealthChecksSmoke:
    """Smoke tests for health check system."""

    def test_health_checker_instantiates(self) -> None:
        """Verify health checker can be created."""
        from packages.health.checks import HealthChecker, HealthStatus

        checker = HealthChecker()
        assert checker.get_overall_status() == HealthStatus.UNHEALTHY

    def test_disk_space_check_runs(self) -> None:
        """Verify disk space check executes."""
        import asyncio
        from packages.health.checks import check_disk_space

        result = asyncio.run(check_disk_space())
        assert result.name == "disk_space"
        assert result.status.value in ["healthy", "degraded"]


class TestObservabilitySmoke:
    """Smoke tests for observability."""

    def test_metrics_record_functions(self) -> None:
        """Verify metrics functions work."""
        from packages.observability.metrics import (
            record_http_request,
            record_domain_created,
            record_swarm_invocation,
            record_plugin_execution,
            record_canvas_operation,
            record_auth_event,
        )

        # Should not raise
        record_http_request("GET", "/health", 200, 0.1)
        record_domain_created("test")
        record_swarm_invocation("test-domain", 1.0)
        record_plugin_execution("test-plugin", "success", 0.5)
        record_canvas_operation("create", "domain")
        record_auth_event("login", "success")

    def test_logging_config(self) -> None:
        """Verify logging configuration works."""
        from packages.observability.logging import configure_logging, get_logger

        configure_logging(json_logs=False)
        logger = get_logger("test")
        #logge.info("test_event", test=True)  # Won't print if no handler


class TestMiddlewareSmoke:
    """Smoke tests for middleware."""

    def test_middleware_imports(self) -> None:
        """Verify middleware imports."""
        from services.api.middleware import (
            RequestIDMiddleware,
            RateLimitMiddleware,
            HealthCheckMiddleware,
            SecurityHeadersMiddleware,
            RequestSizeLimitMiddleware,
        )

        assert RequestIDMiddleware is not None
        assert RateLimitMiddleware is not None
        assert HealthCheckMiddleware is not None
        assert SecurityHeadersMiddleware is not None
        assert RequestSizeLimitMiddleware is not None


class TestProductionConfiguration:
    """Verify production configuration."""

    def test_env_production_template_exists(self) -> None:
        """Verify .env.production template exists."""
        from pathlib import Path

        env_file = Path("/home/catchyosuser1/AetherOS/.env.production")
        assert env_file.exists()
        content = env_file.read_text()
        assert "JWT_SECRET_KEY=" in content
        assert "DATABASE_URL=" in content

    def test_docker_compose_structure(self) -> None:
        """Verify docker-compose has required services."""
        from pathlib import Path

        compose_file = Path("/home/catchyosuser1/AetherOS/docker-compose.yml")
        content = compose_file.read_text()

        assert "postgres:" in content
        assert "redis:" in content
        assert "api:" in content
        assert "prometheus:" in content
        assert "jaeger:" in content
        assert "grafana:" in content

    def test_documentation_exists(self) -> None:
        """Verify all documentation files exist."""
        from pathlib import Path

        docs = Path("/home/catchyosuser1/AetherOS/docs")
        assert (docs / "DEPLOYMENT.md").exists()
        assert (docs / "API.md").exists()
        assert (docs / "USER_GUIDE.md").exists()
        assert (docs / "LIVING_SPEC.md").exists()
        assert (docs / "RELEASE_CHECKLIST.md").exists()


class TestVersionConsistency:
    """Verify version numbers are consistent."""

    def test_pyproject_version(self) -> None:
        """Verify pyproject.toml has version."""
        import tomllib
        from pathlib import Path

        pyproject = Path("/home/catchyosuser1/AetherOS/pyproject.toml")
        content = pyproject.read_bytes()
        data = tomllib.loads(content.decode())
        assert data["project"]["version"] == "0.1.0"

    def test_main_app_version(self) -> None:
        """Verify FastAPI app has version."""
        from services.api.main import app

        # The version is set in the app initialization
        # We can't easily test this without importing the full app
        # but we can verify the main.py file contains the version
        from pathlib import Path

        main_file = Path("/home/catchyosuser1/AetherOS/services/api/main.py")
        content = main_file.read_text()
        assert 'version="0.1.0"' in content


class TestMonitoringSetup:
    """Verify monitoring configuration."""

    def test_prometheus_config_exists(self) -> None:
        """Verify Prometheus config exists."""
        from pathlib import Path

        config = Path("/home/catchyosuser1/AetherOS/monitoring/prometheus.yml")
        assert config.exists()
        content = config.read_text()
        assert "inkosai-api" in content

    def test_grafana_dashboards_exist(self) -> None:
        """Verify Grafana dashboards exist."""
        from pathlib import Path

        dashboards = Path("/home/catchyosuser1/AetherOS/monitoring/grafana/dashboards")
        assert (dashboards / "inkosai-overview.json").exists()
        assert (dashboards / "dashboard.yml").exists()

    def test_grafana_datasources_exist(self) -> None:
        """Verify Grafana datasources config exists."""
        from pathlib import Path

        datasources = Path("/home/catchyosuser1/AetherOS/monitoring/grafana/datasources")
        assert (datasources / "prometheus.yml").exists()


class TestCISetup:
    """Verify CI/CD configuration."""

    def test_github_workflows_exist(self) -> None:
        """Verify GitHub Actions workflow exists."""
        from pathlib import Path

        ci_file = Path("/home/catchyosuser1/AetherOS/.github/workflows/ci.yml")
        assert ci_file.exists()
        content = ci_file.read_text()
        assert "python-tests" in content
        assert "nextjs-build" in content
        assert "docker-build" in content

    def test_dockerfile_exists(self) -> None:
        """Verify Dockerfile exists."""
        from pathlib import Path

        dockerfile = Path("/home/catchyosuser1/AetherOS/Dockerfile")
        assert dockerfile.exists()
        content = dockerfile.read_text()
        assert "production" in content.lower()
        assert "inkosai" in content.lower()


class TestChangelog:
    """Verify changelog completeness."""

    def test_changelog_exists(self) -> None:
        """Verify CHANGELOG.md exists."""
        from pathlib import Path

        changelog = Path("/home/catchyosuser1/AetherOS/CHANGELOG.md")
        assert changelog.exists()
        content = changelog.read_text()
        assert "0.1.0" in content
        assert "## [0.1.0]" in content
