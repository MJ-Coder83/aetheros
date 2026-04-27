"""InkosAI Observability Module — OpenTelemetry, structured logging, and metrics."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI

from packages.observability.logging import configure_logging, get_logger
from packages.observability.metrics import configure_metrics, get_meter
from packages.observability.tracing import configure_tracing, get_tracer

__all__ = [
    "configure_logging",
    "configure_metrics",
    "configure_tracing",
    "get_logger",
    "get_meter",
    "get_tracer",
    "setup_observability",
]


def setup_observability(app: FastAPI | None = None) -> None:
    """Initialize all observability components.

    Args:
        app: Optional FastAPI app to instrument
    """
    configure_logging()
    configure_tracing(app)
    configure_metrics(app)
