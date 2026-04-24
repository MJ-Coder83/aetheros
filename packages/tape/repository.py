"""Tape repository — database and in-memory persistence implementations.

The repository handles all CRUD-like operations (append-only for writes, rich
querying for reads). Two backends are provided:

- TapeRepository:      async SQLAlchemy against PostgreSQL (production)
- InMemoryTapeRepository: in-memory list for testing and local dev
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.tape.models import TapeEntry
from packages.tape.schemas import TapeEntryCreate, TapeEntryFilter
from services.api.database import TapeEntryORM

if TYPE_CHECKING:
    pass


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

    Accepts either an active AsyncSession or an async_sessionmaker. When a
    sessionmaker is provided, each operation runs in its own session and
    transaction, making the repository safe to use as a singleton.
    """

    def __init__(
        self,
        session_or_maker: AsyncSession | async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session: AsyncSession | None = (
            session_or_maker if isinstance(session_or_maker, AsyncSession) else None
        )
        self._maker: async_sessionmaker[AsyncSession] | None = (
            session_or_maker if isinstance(session_or_maker, async_sessionmaker) else None
        )

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        if self._maker is not None:
            return self._maker()
        raise RuntimeError("TapeRepository requires an AsyncSession or async_sessionmaker")

    async def log_event(self, entry: TapeEntryCreate) -> TapeEntry:
        session = await self._get_session()
        row = TapeEntryORM(
            event_type=entry.event_type,
            agent_id=entry.agent_id,
            payload=entry.payload,
            metadata=entry.metadata,
            commit_id=str(entry.commit_id) if entry.commit_id is not None else None,
        )
        session.add(row)
        await session.flush()
        result = _orm_to_model(row)
        if self._maker is not None:
            await session.commit()
            await session.close()
        return result

    async def get_entry_by_id(self, entry_id: UUID) -> TapeEntry | None:
        session = await self._get_session()
        result = await session.execute(
            select(TapeEntryORM).where(TapeEntryORM.id == str(entry_id))
        )
        row = result.scalar_one_or_none()
        if self._maker is not None:
            await session.close()
        if row is None:
            return None
        return _orm_to_model(row)

    async def get_entries(self, filters: TapeEntryFilter) -> list[TapeEntry]:
        session = await self._get_session()
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
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        if self._maker is not None:
            await session.close()
        return [_orm_to_model(row) for row in rows]

    async def get_recent_entries(self, limit: int = 50) -> list[TapeEntry]:
        session = await self._get_session()
        result = await session.execute(
            select(TapeEntryORM).order_by(TapeEntryORM.timestamp.desc()).limit(limit)
        )
        rows = list(result.scalars().all())
        if self._maker is not None:
            await session.close()
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
