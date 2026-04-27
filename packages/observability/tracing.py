"""OpenTelemetry tracing configuration for InkosAI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

if TYPE_CHECKING:
    from fastapi import FastAPI

# Global tracer provider
tracer_provider: TracerProvider | None = None
propagator = TraceContextTextMapPropagator()


def configure_tracing(app: FastAPI | None = None, service_name: str = "inkosai-api") -> None:
    """Configure OpenTelemetry tracing.

    Args:
        app: Optional FastAPI app to instrument
        service_name: Service name for traces
    """
    global tracer_provider

    if tracer_provider is not None:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment": "production",
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Export to OTLP (can be received by Jaeger, Tempo, etc.)
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4318/v1/traces",  # Default OTLP HTTP endpoint
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrument FastAPI if provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str = "inkosai") -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Tracer name

    Returns:
        OpenTelemetry tracer
    """
    return trace.get_tracer(name)


def get_current_span() -> trace.Span | None:
    """Get the current active span."""
    return trace.get_current_span()


def add_span_attribute(key: str, value: str | int | float | bool) -> None:
    """Add an attribute to the current span."""
    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict | None = None) -> None:
    """Add an event to the current span."""
    span = get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes)
