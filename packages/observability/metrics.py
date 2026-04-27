"""Prometheus metrics for InkosAI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

if TYPE_CHECKING:
    from fastapi import FastAPI

# Request metrics
http_requests_total = Counter(
    "inkosai_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration = Histogram(
    "inkosai_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Domain metrics
domains_created_total = Counter(
    "inkosai_domains_created_total",
    "Total domains created",
    ["domain_type"],
)

swarm_invocations_total = Counter(
    "inkosai_swarm_invocations_total",
    "Total swarm invocations",
    ["domain"],
)

swarm_invocation_duration = Histogram(
    "inkosai_swarm_invocation_duration_seconds",
    "Swarm invocation duration",
    ["domain"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# Plugin metrics
plugins_executed_total = Counter(
    "inkosai_plugins_executed_total",
    "Total plugin executions",
    ["plugin_id", "status"],
)

plugin_execution_duration = Histogram(
    "inkosai_plugin_execution_duration_seconds",
    "Plugin execution duration",
    ["plugin_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Canvas metrics
canvas_operations_total = Counter(
    "inkosai_canvas_operations_total",
    "Total canvas operations",
    ["operation", "canvas_type"],
)

# Authentication metrics
auth_events_total = Counter(
    "inkosai_auth_events_total",
    "Total authentication events",
    ["event_type", "result"],
)

# Health metrics
health_check_duration = Histogram(
    "inkosai_health_check_duration_seconds",
    "Health check duration",
    ["check_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)

db_connections_active = Gauge(
    "inkosai_db_connections_active",
    "Active database connections",
)

redis_connections_active = Gauge(
    "inkosai_redis_connections_active",
    "Active Redis connections",
)


def configure_metrics(app: FastAPI | None = None) -> None:
    """Configure Prometheus metrics.

    Args:
        app: Optional FastAPI app to add metrics endpoint to
    """
    if app is not None:
        from fastapi.responses import Response

        @app.get("/metrics")
        async def metrics() -> Response:
            """Prometheus metrics endpoint."""
            return Response(
                content=generate_latest(),
                media_type=CONTENT_TYPE_LATEST,
            )


def get_meter() -> None:
    """Get metrics registry (placeholder for OTLP metrics)."""
    pass


def record_http_request(method: str, endpoint: str, status_code: int, duration: float) -> None:
    """Record an HTTP request."""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def record_domain_created(domain_type: str) -> None:
    """Record a domain creation."""
    domains_created_total.labels(domain_type=domain_type).inc()


def record_swarm_invocation(domain: str, duration: float) -> None:
    """Record a swarm invocation."""
    swarm_invocations_total.labels(domain=domain).inc()
    swarm_invocation_duration.labels(domain=domain).observe(duration)


def record_plugin_execution(plugin_id: str, status: str, duration: float) -> None:
    """Record a plugin execution."""
    plugins_executed_total.labels(plugin_id=plugin_id, status=status).inc()
    plugin_execution_duration.labels(plugin_id=plugin_id).observe(duration)


def record_canvas_operation(operation: str, canvas_type: str) -> None:
    """Record a canvas operation."""
    canvas_operations_total.labels(operation=operation, canvas_type=canvas_type).inc()


def record_auth_event(event_type: str, result: str) -> None:
    """Record an authentication event."""
    auth_events_total.labels(event_type=event_type, result=result).inc()
