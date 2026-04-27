"""Structured JSON logging with correlation IDs for InkosAI."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import LoggerFactory, filter_by_level

# Context variable for correlation/request ID
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def add_correlation_id(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add correlation ID to log entry."""
    corr_id = correlation_id.get()
    if corr_id:
        event_dict["correlation_id"] = corr_id
    return event_dict


def add_service_info(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add service metadata to log entry."""
    event_dict["service"] = "inkosai-api"
    event_dict["version"] = "0.1.0"
    return event_dict


def configure_logging(json_logs: bool = True) -> None:
    """Configure structured logging for production.

    Args:
        json_logs: Whether to output JSON formatted logs
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        filter_by_level,
        add_correlation_id,
        add_service_info,
        TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        shared_processors.append(JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (module name)

    Returns:
        Configured structured logger
    """
    return structlog.get_logger(name)


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id.set(cid)


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return correlation_id.get()
