"""Pydantic schemas for Tape API requests and responses.

- TapeEntryCreate: inbound payload for logging a new event
- TapeEntryRead: outbound representation returned to callers
- TapeEntryFilter: query parameters for searching entries
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TapeEntryCreate(BaseModel):
    """Schema for creating a new Tape entry.

    The server assigns `id` and `timestamp` automatically.
    """

    event_type: str
    agent_id: str | None = None
    payload: dict[str, object]
    metadata: dict[str, object] = {}
    commit_id: UUID | None = None


class TapeEntryRead(BaseModel):
    """Schema for reading a Tape entry back to the caller."""

    id: UUID
    timestamp: datetime
    event_type: str
    agent_id: str | None = None
    payload: dict[str, object]
    metadata: dict[str, object] = {}
    commit_id: UUID | None = None


class TapeEntryFilter(BaseModel):
    """Query filters for searching Tape entries.

    All fields are optional — omit everything to get the most recent entries.
    """

    event_type: str | None = None
    agent_id: str | None = None
    commit_id: UUID | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None
    limit: int = Field(default=50, ge=1, le=1000)
