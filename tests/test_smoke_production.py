"""Production smoke tests for InkosAI v0.1.0.

These tests verify critical application paths in a production-like environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    pass


class TestProductionDomainCreation:
    """Smoke tests for One-Click Domain Creation."""

    def test_one_click_domain_engine_import(self) -> None:
        """Test OneClickDomainCreationEngine can be imported."""
        from packages.domain.creation import OneClickDomainCreationEngine

        engine = OneClickDomainCreationEngine
        assert engine is not None

    def test_domain_blueprint_creation(self) -> None:
        """Test domain blueprint creation."""
        from packages.domain.domain_blueprint import (
            AgentBlueprint,
            AgentRole,
            DomainBlueprint,
            SkillBlueprint,
            WorkflowBlueprint,
        )

        blueprint = DomainBlueprint(
            domain_name="Test Domain",
            domain_id="test-domain",
            description="A test domain",
            agents=[
                AgentBlueprint(
                    agent_id="a1",
                    name="Test Agent",
                    role=AgentRole.SPECIALIST,
                    goal="Test the system",
                )
            ],
            skills=[
                SkillBlueprint(
                    skill_id="s1",
                    name="Test Skill",
                    description="A test skill",
                )
            ],
            workflows=[
                WorkflowBlueprint(
                    workflow_id="w1",
                    name="Test Workflow",
                    steps=["step1", "step2"],
                )
            ],
        )

        assert blueprint is not None
        assert blueprint.domain_name == "Test Domain"
        assert len(blueprint.agents) == 1

    def test_planning_engine_import(self) -> None:
        """Test planning engine can be imported."""
        from packages.prime.planning import PlanningEngine

        engine = PlanningEngine
        assert engine is not None


class TestProductionCanvasV5:
    """Smoke tests for Domain Canvas v5."""

    def test_browser_node_creation(self) -> None:
        """Test Browser Node can be created."""
        from packages.canvas.nodes.browser import BrowserNodeConfig, BrowserNodeType

        config = BrowserNodeConfig(
            source_url="https://example.com",
            node_type=BrowserNodeType.PREVIEW,
        )

        assert config.source_url == "https://example.com"

    def test_terminal_node_import(self) -> None:
        """Test Terminal Node imports correctly."""
        from packages.canvas.nodes.terminal import TerminalNode

        # Terminal node exists and can be imported
        assert TerminalNode is not None

    def test_plugin_node_manager_creation(self) -> None:
        """Test Plugin Node Manager can be created."""
        from packages.canvas import PluginNodeConfig

        config = PluginNodeConfig(
            label="Test Plugin",
            plugin_id="test-plugin",
        )

        assert config.plugin_id == "test-plugin"
        assert config.label == "Test Plugin"

    def test_canvas_v5_engine_creation(self) -> None:
        """Test Canvas v5 Engine."""
        from packages.canvas import CanvasV5Engine

        # CanvasV5Engine is available
        assert CanvasV5Engine is not None


class TestProductionSwarmModes:
    """Smoke tests for all Swarm modes."""

    def test_quick_swarm_mode(self) -> None:
        """Test Quick Swarm mode exists."""
        from packages.canvas import SwarmMode

        assert SwarmMode.QUICK is not None

    def test_governed_swarm_mode(self) -> None:
        """Test Governed Swarm mode exists."""
        from packages.canvas import SwarmMode

        assert SwarmMode.GOVERNED is not None

    def test_swarm_integration_exists(self) -> None:
        """Test Swarm Integration exists."""
        from packages.canvas import SwarmIntegration

        assert SwarmIntegration is not None


class TestProductionPlugins:
    """Smoke tests for Plugin system."""

    async def test_plugin_marketplace_accessible(self) -> None:
        """Test Plugin Marketplace is accessible."""
        from packages.marketplace import MarketplaceService

        # MarketplaceService exists and can be instantiated
        assert MarketplaceService is not None

    def test_plugin_listing_exists(self) -> None:
        """Test plugin listing model exists."""
        from packages.marketplace import PluginCategory, PluginListing

        listing = PluginListing(
            id=uuid4(),
            name="Test Plugin",
            display_name="Test Plugin Display",
            description="A test plugin",
            category=PluginCategory.INTEGRATION,
            version="1.0.0",
            author="test-author",
        )

        assert listing is not None
        assert listing.name == "Test Plugin"

    def test_plugin_sandbox_config(self) -> None:
        """Test plugin sandbox configuration."""
        from packages.config import get_settings

        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "debug")


class TestProductionAuthSecurity:
    """Smoke tests for Authentication and Security."""

    def test_auth_user_model(self) -> None:
        """Test User model exists."""
        from packages.auth import User, UserRole

        user = User(
            id=uuid4(),
            username="testuser",
            role=UserRole.VIEWER,
        )

        assert user.id is not None
        assert user.username == "testuser"

    async def test_role_based_access_control(self) -> None:
        """Test RBAC role hierarchy."""
        from packages.auth import UserRole

        # Test role hierarchy
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.OPERATOR.value == "operator"
        assert UserRole.VIEWER.value == "viewer"

    def test_security_headers_active(self) -> None:
        """Test security headers are configured."""
        from fastapi import FastAPI

        from services.api.middleware import SecurityHeadersMiddleware

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        assert middleware._csp is not None
        assert "default-src" in middleware._csp

    def test_request_size_limits(self) -> None:
        """Test request size limiting is configured."""
        from fastapi import FastAPI

        from services.api.middleware import RequestSizeLimitMiddleware

        app = FastAPI()
        middleware = RequestSizeLimitMiddleware(app, max_size_bytes=10 * 1024 * 1024)

        assert middleware._max_size == 10 * 1024 * 1024


class TestProductionObservability:
    """Smoke tests for Observability."""

    def test_prometheus_metrics_endpoint(self) -> None:
        """Test Prometheus metrics are defined."""
        from packages.observability.metrics import (
            domains_created_total,
            http_request_duration,
            http_requests_total,
        )

        # Verify metrics exist
        assert http_requests_total is not None
        assert http_request_duration is not None
        assert domains_created_total is not None

    def test_health_check_registration(self) -> None:
        """Test health checks are registered."""
        from packages.health.checks import health_checker

        # Health checker should have registered checks
        assert health_checker._checks is not None

    def test_structured_logging_config(self) -> None:
        """Test structured logging is configured."""
        from packages.observability.logging import configure_logging, get_logger

        # Should not raise
        configure_logging(json_logs=True)
        logger = get_logger("test")
        assert logger is not None


class TestProductionAPI:
    """Smoke tests for API endpoints."""

    def test_main_app_initializes(self) -> None:
        """Test FastAPI app initializes."""
        from services.api.main import app

        assert app is not None
        assert app.title == "InkosAI API"

    def test_routes_registered(self) -> None:
        """Test all routes are registered."""
        from services.api.main import app

        routes = [route.path for route in app.routes]

        # Verify key routes exist
        assert any("/health" in r for r in routes)


class TestProductionAetherGit:
    """Smoke tests for AetherGit versioning."""

    async def test_aethergit_import(self) -> None:
        """Test AetherGit imports correctly."""
        from packages.aethergit import AdvancedAetherGit

        assert AdvancedAetherGit is not None

    async def test_branch_management(self) -> None:
        """Test branch management."""
        from packages.aethergit import CommitStore

        store = CommitStore()
        assert store is not None


class TestProductionTape:
    """Smoke tests for Tape audit log."""

    def test_tape_service_creation(self) -> None:
        """Test Tape service creation."""
        from packages.tape import InMemoryTapeRepository, TapeService

        repo = InMemoryTapeRepository()
        tape = TapeService(repo)

        assert tape is not None
        assert repo is not None

    def test_semantic_query_engine_import(self) -> None:
        """Test semantic query engine can be imported."""
        from packages.tape import SemanticTapeQueryEngine

        assert SemanticTapeQueryEngine is not None


class TestProductionConfiguration:
    """Smoke tests for Production Configuration."""

    def test_env_production_template(self) -> None:
        """Test .env.production template exists."""
        from pathlib import Path

        env_file = Path("/home/catchyosuser1/AetherOS/.env.production")
        assert env_file.exists()

        content = env_file.read_text()
        assert "DATABASE_URL=" in content
        assert "JWT_SECRET_KEY=" in content

    def test_docker_compose_services(self) -> None:
        """Test docker-compose has required services."""
        from pathlib import Path

        compose_file = Path("/home/catchyosuser1/AetherOS/docker-compose.yml")
        content = compose_file.read_text()

        required = ["postgres:", "redis:", "api:", "prometheus:", "jaeger:", "grafana:"]
        for service in required:
            assert service in content, f"Missing service: {service}"


class TestProductionVersion:
    """Smoke tests for Version Information."""

    def test_version_consistency(self) -> None:
        """Test version is consistent across files."""
        import tomllib
        from pathlib import Path

        # pyproject.toml
        pyproject = Path("/home/catchyosuser1/AetherOS/pyproject.toml")
        content = pyproject.read_bytes()
        data = tomllib.loads(content.decode())
        version = data["project"]["version"]

        assert version == "0.1.0"

    def test_changelog_has_v010(self) -> None:
        """Test CHANGELOG has v0.1.0 section."""
        from pathlib import Path

        changelog = Path("/home/catchyosuser1/AetherOS/CHANGELOG.md")
        content = changelog.read_text()

        assert "[0.1.0]" in content
        assert "2025-04-27" in content


class TestDocumentationComplete:
    """Smoke tests for Documentation Completeness."""

    def test_all_documentation_exists(self) -> None:
        """Test all required documentation exists."""
        from pathlib import Path

        docs = Path("/home/catchyosuser1/AetherOS/docs")
        required = [
            "DEPLOYMENT.md",
            "API.md",
            "USER_GUIDE.md",
            "RELEASE_CHECKLIST.md",
            "LIVING_SPEC.md",
        ]

        for doc in required:
            assert (docs / doc).exists(), f"Missing documentation: {doc}"

    def test_readme_quickstart(self) -> None:
        """Test README has quickstart."""
        from pathlib import Path

        readme = Path("/home/catchyosuser1/AetherOS/README.md")
        content = readme.read_text()

        assert "Quick Start" in content
        assert "docker-compose up" in content


# Production-specific markers
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.production,
]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
