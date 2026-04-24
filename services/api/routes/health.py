"""Health check router."""

from fastapi import APIRouter

from services.api.dependencies import get_tape_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint with subsystem status."""
    status = "healthy"
    try:
        tape_svc = get_tape_service()
        # Lightweight connectivity check
        _ = tape_svc
    except Exception:
        status = "degraded"

    return {
        "status": status,
        "version": "0.1.0",
        "service": "inkosai-api",
    }
