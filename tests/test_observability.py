"""Observability and metrics tests."""


import pytest

from packages.observability.logging import (
    add_correlation_id,
    add_service_info,
    get_correlation_id,
    set_correlation_id,
)


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_correlation_id_context_var(self) -> None:
        """Test correlation ID can be set and retrieved."""
        test_cid = "test-correlation-id-123"
        set_correlation_id(test_cid)

        assert get_correlation_id() == test_cid

        # Clear after test
        set_correlation_id(None)

    def test_add_correlation_id_with_cid(self) -> None:
        """Test correlation ID is added when set."""
        set_correlation_id("test-cid")

        event_dict = {}
        result = add_correlation_id(None, "info", event_dict)

        assert result["correlation_id"] == "test-cid"

        set_correlation_id(None)

    def test_add_correlation_id_without_cid(self) -> None:
        """Test correlation ID not added when not set."""
        set_correlation_id(None)

        event_dict = {}
        result = add_correlation_id(None, "info", event_dict)

        assert "correlation_id" not in result

    def test_add_service_info(self) -> None:
        """Test service info is added to log entry."""
        event_dict = {}
        result = add_service_info(None, "info", event_dict)

        assert result["service"] == "inkosai-api"
        assert result["version"] == "0.1.0"


class TestTracing:
    """Test OpenTelemetry tracing functionality."""

    @pytest.mark.integration
    def test_get_tracer_returns_tracer(self) -> None:
        """Test tracer can be obtained."""
        try:
            from packages.observability.tracing import get_tracer

            tracer = get_tracer("test")
            assert tracer is not None
        except ImportError:
            pytest.skip("Opentelemetry not installed")


class TestMetrics:
    """Test Prometheus metrics."""

    def test_metrics_imports(self) -> None:
        """Test metrics module imports correctly."""
        from packages.observability.metrics import (
            domains_created_total,
            http_request_duration,
            http_requests_total,
            plugins_executed_total,
            swarm_invocations_total,
        )

        assert http_requests_total is not None
        assert http_request_duration is not None
        assert domains_created_total is not None
        assert swarm_invocations_total is not None
        assert plugins_executed_total is not None

    def test_record_http_request(self) -> None:
        """Test HTTP request recording."""
        from packages.observability.metrics import record_http_request

        # Should not raise
        record_http_request("GET", "/api/health", 200, 0.1)

    def test_record_domain_created(self) -> None:
        """Test domain creation recording."""
        from packages.observability.metrics import record_domain_created

        # Should not raise
        record_domain_created("user")

    def test_record_swarm_invocation(self) -> None:
        """Test swarm invocation recording."""
        from packages.observability.metrics import record_swarm_invocation

        # Should not raise
        record_swarm_invocation("test-domain", 1.5)

    def test_record_plugin_execution(self) -> None:
        """Test plugin execution recording."""
        from packages.observability.metrics import record_plugin_execution

        # Should not raise
        record_plugin_execution("test-plugin", "success", 0.5)

    def test_record_canvas_operation(self) -> None:
        """Test canvas operation recording."""
        from packages.observability.metrics import record_canvas_operation

        # Should not raise
        record_canvas_operation("create", "domain")

    def test_record_auth_event(self) -> None:
        """Test auth event recording."""
        from packages.observability.metrics import record_auth_event

        # Should not raise
        record_auth_event("login", "success")
