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


# ---------------------------------------------------------------------------
# Security headers middleware (CSP, HSTS, X-Frame-Options, etc.)
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Implements security best practices:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - Strict-Transport-Security
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(
        self,
        app: FastAPI,
        csp_policy: str | None = None,
    ) -> None:
        super().__init__(app)
        self._csp = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = self._csp

        return response


# ---------------------------------------------------------------------------
# Request size limit middleware
# ---------------------------------------------------------------------------


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request payload size."""

    def __init__(
        self,
        app: FastAPI,
        max_size_bytes: int = 10 * 1024 * 1024,  # 10MB default
    ) -> None:
        super().__init__(app)
        self._max_size = max_size_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self._max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request too large. Max size: {self._max_size} bytes"},
                    )
            except ValueError:
                pass

        # Also check actual body size for chunked transfers
        body = await request.body()
        if len(body) > self._max_size:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request too large. Max size: {self._max_size} bytes"},
            )

        # Recreate request with body for downstream handlers
        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive, request._send)
        return await call_next(request)
