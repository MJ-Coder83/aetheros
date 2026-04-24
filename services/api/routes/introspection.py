"""Historical Analysis and Introspection API routes."""

from fastapi import APIRouter

from services.api.dependencies import IntrospectorForAnalysisDep

router = APIRouter(prefix="/introspection", tags=["introspection"])


@router.post("/historical")
async def historical_analysis(
    svc: IntrospectorForAnalysisDep,
    from_time: str | None = None,
    to_time: str | None = None,
    bucket_size_minutes: int = 60,
) -> dict[str, object]:
    """Perform a comprehensive historical analysis over the Tape."""
    result = await svc.historical_analysis(
        from_time=from_time,
        to_time=to_time,
        bucket_size_minutes=bucket_size_minutes,
    )
    return result.model_dump()


@router.post("/temporal-query")
async def temporal_query(
    svc: IntrospectorForAnalysisDep,
    from_time: str | None = None,
    to_time: str | None = None,
    event_type: str | None = None,
    agent_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, object]]:
    """Query the Tape with temporal filters."""
    entries = await svc.temporal_query(
        from_time=from_time,
        to_time=to_time,
        event_type=event_type,
        agent_id=agent_id,
        limit=limit,
    )
    return [e.model_dump() for e in entries]
