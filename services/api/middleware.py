"""InkosAI API middleware — request ID propagation, rate limiting, and health."""

import time
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every incoming request.

    The ID is propagated via the ``X-Request-ID`` header. If the client
    provides one, it is reused; otherwise a new UUID is generated. The
    ID is stored in ``request.state.request_id`` and included in the
    response headers.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# Rate limiting middleware (in-memory, per-client)
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.

    Tracks requests per client IP in a sliding window. Returns 429 when
    the limit is exceeded. This is a pragmatic stop-gap; production
    deployments should use Redis-backed rate limiting.
    """

    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 120,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._max_requests = max_requests
        self._window = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Prune old entries
        self._clients[client_ip] = [
            ts for ts in self._clients[client_ip] if now - ts < self._window
        ]

        if len(self._clients[client_ip]) >= self._max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please slow down."
                },
            )

        self._clients[client_ip].append(now)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Health check middleware (enrich response)
# ---------------------------------------------------------------------------


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Enrich the health check endpoint with timing and request metadata."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path == "/health":
            start = time.time()
            response = await call_next(request)
            duration_ms = round((time.time() - start) * 1000, 2)
            response.headers["X-Health-Check-Duration-Ms"] = str(duration_ms)
            return response
        return await call_next(request)
