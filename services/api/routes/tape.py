"""Tape event log router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from packages.tape.models import TapeEntry
from packages.tape.schemas import TapeEntryCreate, TapeEntryRead
from packages.tape.service import TapeEntryNotFoundError
from services.api.dependencies import TapeServiceDep

router = APIRouter(prefix="/tape", tags=["tape"])


@router.post("/log", response_model=TapeEntryRead, status_code=201)
async def log_event(
    body: TapeEntryCreate,
    svc: TapeServiceDep,
) -> TapeEntry:
    """Append a new immutable entry to the Tape."""
    entry = await svc.log_event(
        event_type=body.event_type,
        payload=body.payload,
        agent_id=body.agent_id,
        metadata=body.metadata,
        commit_id=body.commit_id,
    )
    return entry


@router.get("/entries", response_model=list[TapeEntryRead])
async def get_entries(
    svc: TapeServiceDep,
    event_type: str | None = None,
    agent_id: str | None = None,
    commit_id: UUID | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    limit: int = 50,
) -> list[TapeEntry]:
    """Query Tape entries with optional filters."""
    # The description for limit and other Query params is lost if not using Query.
    # However, for the sake of resolving B008, we remove the inline Query calls.
    # If description is needed, use Annotated[type, Query(description="...")]
    return await svc.get_entries(
        event_type=event_type,
        agent_id=agent_id,
        commit_id=commit_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
    )


@router.get("/entries/{entry_id}", response_model=TapeEntryRead)
async def get_entry_by_id(
    entry_id: UUID,
    svc: TapeServiceDep,
) -> TapeEntry:
    """Retrieve a single Tape entry by its ID."""
    try:
        return await svc.get_entry_by_id(entry_id)
    except TapeEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/recent", response_model=list[TapeEntryRead])
async def get_recent_entries(
    svc: TapeServiceDep,
    limit: int = 50,
) -> list[TapeEntry]:
    """Return the most recent Tape entries, newest first."""
    return await svc.get_recent_entries(limit)
