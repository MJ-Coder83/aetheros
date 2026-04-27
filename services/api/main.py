"""InkosAI API — FastAPI application with modular routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from packages.health import create_health_router
from packages.observability import setup_observability
from services.api.database import init_db
from services.api.middleware import (
    HealthCheckMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
)
from services.api.routes import (
    aethergit,
    auth,
    canvas,
    debates,
    domains,
    explainability,
    folder_tree,
    health,
    introspection,
    knowledge,
    llm_planning,
    marketplace,
    nlq,
    plans,
    plugins,
    prime,
    profiles,
    settings,
    tape,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler — initialise database and observability on startup."""
    # Initialize observability (logging, tracing, metrics)
    setup_observability(app)
    await init_db()
    yield


app = FastAPI(
    title="InkosAI API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)  # Security headers on all responses
app.add_middleware(RequestSizeLimitMiddleware, max_size_bytes=10 * 1024 * 1024)  # 10MB limit
app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)  # type: ignore
app.add_middleware(HealthCheckMiddleware)

# Include all routers
# Health checks first (must be available for k8s probes)
app.include_router(create_health_router())
app.include_router(health.router)
app.include_router(tape.router)
app.include_router(aethergit.router)
app.include_router(debates.router)
app.include_router(explainability.router)
app.include_router(plans.router)
app.include_router(domains.router)
app.include_router(knowledge.router)
app.include_router(profiles.router)
app.include_router(prime.router)
app.include_router(llm_planning.router)
app.include_router(introspection.router)
app.include_router(nlq.router)
app.include_router(auth.router)
app.include_router(folder_tree.router)
app.include_router(canvas.router)
app.include_router(plugins.router)
app.include_router(marketplace.router)
app.include_router(settings.router)
