"""Tape service — high-level operations on the immutable event log.

The service wraps the repository and adds:
- Validation and business logic before persistence
- Automatic enrichment (e.g. setting commit_id from AetherGit context)
- Clean error handling with domain-specific exceptions
"""

from uuid import UUID

from packages.tape.models import TapeEntry
from packages.tape.repository import AbstractTapeRepository
from packages.tape.schemas import TapeEntryCreate, TapeEntryFilter


class TapeError(Exception):
    """Base exception for Tape operations."""


class TapeEntryNotFoundError(TapeError):
    """Raised when a requested Tape entry does not exist."""


class TapeService:
    """Application service for the Tape subsystem.

    Usage::

        repo = InMemoryTapeRepository()          # or TapeRepository(session)
        svc  = TapeService(repo)
        entry = await svc.log_event(...)
    """

    def __init__(self, repo: AbstractTapeRepository) -> None:
        self._repo = repo

    async def log_event(
        self,
        event_type: str,
        payload: dict[str, object],
        agent_id: str | None = None,
        metadata: dict[str, object] | None = None,
        commit_id: UUID | None = None,
    ) -> TapeEntry:
        """Append a new immutable entry to the Tape.

        Args:
            event_type: Categorises the event (e.g. "agent.invoke", "commit.create").
            payload: Arbitrary JSON-serialisable data attached to the event.
            agent_id: ID of the agent that produced the event.
            metadata: Optional supplementary key-value metadata.
            commit_id: Optional link to an AetherGit commit.

        Returns:
            The newly created TapeEntry with server-assigned id and timestamp.
        """
        create_schema = TapeEntryCreate(
            event_type=event_type,
            agent_id=agent_id,
            payload=payload,
            metadata=metadata or {},
            commit_id=commit_id,
        )
        return await self._repo.log_event(create_schema)

    async def get_entry_by_id(self, entry_id: UUID) -> TapeEntry:
        """Retrieve a single entry by ID.

        Raises:
            TapeEntryNotFoundError: if no entry with the given ID exists.
        """
        entry = await self._repo.get_entry_by_id(entry_id)
        if entry is None:
            raise TapeEntryNotFoundError(f"Tape entry {entry_id} not found")
        return entry

    async def get_entries(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        commit_id: UUID | None = None,
        from_time: str | None = None,
        to_time: str | None = None,
        limit: int = 50,
    ) -> list[TapeEntry]:
        """Query entries with optional filters.

        All parameters are optional; omit them to get the most recent entries.
        """
        from datetime import datetime as dt

        parsed_from: dt | None = None
        parsed_to: dt | None = None
        if from_time is not None:
            parsed_from = dt.fromisoformat(from_time)
        if to_time is not None:
            parsed_to = dt.fromisoformat(to_time)

        filters = TapeEntryFilter(
            event_type=event_type,
            agent_id=agent_id,
            commit_id=commit_id,
            from_time=parsed_from,
            to_time=parsed_to,
            limit=limit,
        )
        return await self._repo.get_entries(filters)

    async def get_recent_entries(self, limit: int = 50) -> list[TapeEntry]:
        """Return the most recent entries, newest first."""
        return await self._repo.get_recent_entries(limit)
