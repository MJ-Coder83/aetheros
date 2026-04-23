"""AetherOS API — FastAPI application with Tape endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.tape.models import TapeEntry
from packages.tape.repository import InMemoryTapeRepository, TapeRepository
from packages.tape.schemas import TapeEntryCreate, TapeEntryRead
from packages.tape.service import TapeEntryNotFoundError, TapeService
from services.api.database import get_db

app = FastAPI(title="AetherOS API", version="0.1.0")

# ---------------------------------------------------------------------------
# Service instantiation
# For now we use the in-memory repository so the API works without Postgres.
# Swap to TapeRepository(session) when the database is available.
# ---------------------------------------------------------------------------

_tape_service = TapeService(InMemoryTapeRepository())


def _get_tape_service() -> TapeService:
    """Return the singleton TapeService instance."""
    return _tape_service


def _get_db_tape_service(db: AsyncSession = Depends(get_db)) -> TapeService:  # noqa: B008
    """Return a TapeService backed by PostgreSQL (used when DB is connected)."""
    repo = TapeRepository(db)
    return TapeService(repo)


# Type alias for injecting the in-memory TapeService via FastAPI Depends.
TapeServiceDep = Annotated[TapeService, Depends(_get_tape_service)]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Tape endpoints
# ---------------------------------------------------------------------------


@app.post("/tape/log", response_model=TapeEntryRead, status_code=201)
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


@app.get("/tape/entries", response_model=list[TapeEntryRead])
async def get_entries(
    svc: TapeServiceDep,
    event_type: str | None = Query(None, description="Filter by event type"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    commit_id: UUID | None = Query(None, description="Filter by AetherGit commit ID"),  # noqa: B008
    from_time: str | None = Query(None, description="ISO-8601 start timestamp"),
    to_time: str | None = Query(None, description="ISO-8601 end timestamp"),
    limit: int = Query(50, ge=1, le=1000, description="Max entries to return"),
) -> list[TapeEntry]:
    """Query Tape entries with optional filters."""
    return await svc.get_entries(
        event_type=event_type,
        agent_id=agent_id,
        commit_id=commit_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
    )


@app.get("/tape/entries/{entry_id}", response_model=TapeEntryRead)
async def get_entry_by_id(
    entry_id: UUID,
    svc: TapeServiceDep,
) -> TapeEntry:
    """Retrieve a single Tape entry by its ID."""
    try:
        return await svc.get_entry_by_id(entry_id)
    except TapeEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tape/recent", response_model=list[TapeEntryRead])
async def get_recent_entries(
    svc: TapeServiceDep,
    limit: int = Query(50, ge=1, le=1000, description="Max entries to return"),
) -> list[TapeEntry]:
    """Return the most recent Tape entries, newest first."""
    return await svc.get_recent_entries(limit)
