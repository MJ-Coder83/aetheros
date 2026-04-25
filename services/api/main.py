"""InkosAI API — FastAPI application with modular routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.api.database import init_db
from services.api.middleware import (
    HealthCheckMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
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
    nlq,
    plans,
    prime,
    profiles,
    tape,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler — initialise database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="InkosAI API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=120, window_seconds=60)  # type: ignore
app.add_middleware(HealthCheckMiddleware)

# Include all routers
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
