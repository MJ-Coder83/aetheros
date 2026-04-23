"""Pydantic domain models for the Tape system.

TapeEntry is the core immutable record — every agent action produces one.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class TapeEntry(BaseModel):
    """Immutable record of a single agent event.

    The Tape is append-only: entries are never modified or deleted.
    Each entry optionally links to an AetherGit commit via commit_id.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=_utcnow)
    event_type: str
    agent_id: str | None = None
    payload: dict[str, object]
    metadata: dict[str, object] = {}
    commit_id: UUID | None = None
