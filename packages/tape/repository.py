"""Tape repository — database and in-memory persistence implementations.

The repository handles all CRUD-like operations (append-only for writes, rich
querying for reads). Two backends are provided:

- TapeRepository:      async SQLAlchemy against PostgreSQL (production)
- InMemoryTapeRepository: in-memory list for testing and local dev
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, String, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from packages.tape.models import TapeEntry, _utcnow
from packages.tape.schemas import TapeEntryCreate, TapeEntryFilter
from services.api.database import Base

# ---------------------------------------------------------------------------
# SQLAlchemy ORM model (table definition)
# ---------------------------------------------------------------------------


class TapeEntryORM(Base):
    """SQLAlchemy ORM mapping for the ``tape_entries`` table."""

    __tablename__ = "tape_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)
    commit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


def _orm_to_model(row: TapeEntryORM) -> TapeEntry:
    """Convert a TapeEntryORM row to a TapeEntry Pydantic model."""
    return TapeEntry(
        id=UUID(row.id),
        timestamp=row.timestamp,
        event_type=row.event_type,
        agent_id=row.agent_id,
        payload=row.payload if isinstance(row.payload, dict) else {},
        metadata=row.metadata_ if isinstance(row.metadata_, dict) else {},
        commit_id=UUID(row.commit_id) if row.commit_id is not None else None,
    )


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AbstractTapeRepository(ABC):
    """Interface that every Tape persistence backend must implement."""

    @abstractmethod
    async def log_event(self, entry: TapeEntryCreate) -> TapeEntry:
        """Append a new immutable entry to the Tape."""

    @abstractmethod
    async def get_entry_by_id(self, entry_id: UUID) -> TapeEntry | None:
        """Return a single entry by its ID, or None if not found."""

    @abstractmethod
    async def get_entries(self, filters: TapeEntryFilter) -> list[TapeEntry]:
        """Query entries with optional filters (event_type, agent_id, time range)."""

    @abstractmethod
    async def get_recent_entries(self, limit: int = 50) -> list[TapeEntry]:
        """Return the most recent entries, newest first."""


# ---------------------------------------------------------------------------
# SQLAlchemy (PostgreSQL) repository
# ---------------------------------------------------------------------------


class TapeRepository(AbstractTapeRepository):
    """Production repository backed by PostgreSQL via async SQLAlchemy.

    Entries are stored in the ``tape_entries`` table. The table is created
    by ``init_db()`` in ``services.api.database``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_event(self, entry: TapeEntryCreate) -> TapeEntry:
        row = TapeEntryORM(
            event_type=entry.event_type,
            agent_id=entry.agent_id,
            payload=entry.payload,
            metadata=entry.metadata,
            commit_id=str(entry.commit_id) if entry.commit_id is not None else None,
        )
        self._session.add(row)
        await self._session.flush()

        return _orm_to_model(row)

    async def get_entry_by_id(self, entry_id: UUID) -> TapeEntry | None:
        result = await self._session.execute(
            select(TapeEntryORM).where(TapeEntryORM.id == str(entry_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _orm_to_model(row)

    async def get_entries(self, filters: TapeEntryFilter) -> list[TapeEntry]:
        stmt = select(TapeEntryORM).order_by(TapeEntryORM.timestamp.desc())

        from sqlalchemy import ColumnElement

        conditions: list[ColumnElement[bool]] = []
        if filters.event_type is not None:
            conditions.append(TapeEntryORM.event_type == filters.event_type)
        if filters.agent_id is not None:
            conditions.append(TapeEntryORM.agent_id == filters.agent_id)
        if filters.commit_id is not None:
            conditions.append(TapeEntryORM.commit_id == str(filters.commit_id))
        if filters.from_time is not None:
            conditions.append(TapeEntryORM.timestamp >= filters.from_time)
        if filters.to_time is not None:
            conditions.append(TapeEntryORM.timestamp <= filters.to_time)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.limit(filters.limit)
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        return [_orm_to_model(row) for row in rows]

    async def get_recent_entries(self, limit: int = 50) -> list[TapeEntry]:
        result = await self._session.execute(
            select(TapeEntryORM).order_by(TapeEntryORM.timestamp.desc()).limit(limit)
        )
        rows = list(result.scalars().all())
        return [_orm_to_model(row) for row in rows]


# ---------------------------------------------------------------------------
# In-memory repository (for testing)
# ---------------------------------------------------------------------------


class InMemoryTapeRepository(AbstractTapeRepository):
    """Lightweight in-memory Tape store for tests and local development.

    All data is lost when the process exits. Thread-safe for single-threaded
    async code (no concurrent mutation risk under asyncio).
    """

    def __init__(self) -> None:
        self._entries: list[TapeEntry] = []

    async def log_event(self, entry: TapeEntryCreate) -> TapeEntry:
        tape_entry = TapeEntry(
            event_type=entry.event_type,
            agent_id=entry.agent_id,
            payload=entry.payload,
            metadata=entry.metadata,
            commit_id=entry.commit_id,
        )
        self._entries.append(tape_entry)
        return tape_entry

    async def get_entry_by_id(self, entry_id: UUID) -> TapeEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    async def get_entries(self, filters: TapeEntryFilter) -> list[TapeEntry]:
        results = list(self._entries)

        if filters.event_type is not None:
            results = [e for e in results if e.event_type == filters.event_type]
        if filters.agent_id is not None:
            results = [e for e in results if e.agent_id == filters.agent_id]
        if filters.commit_id is not None:
            results = [e for e in results if e.commit_id == filters.commit_id]
        if filters.from_time is not None:
            results = [e for e in results if e.timestamp >= filters.from_time]
        if filters.to_time is not None:
            results = [e for e in results if e.timestamp <= filters.to_time]

        # newest first
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[: filters.limit]

    async def get_recent_entries(self, limit: int = 50) -> list[TapeEntry]:
        sorted_entries = sorted(self._entries, key=lambda e: e.timestamp, reverse=True)
        return sorted_entries[:limit]
