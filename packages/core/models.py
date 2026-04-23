"""AetherOS Core — Domain models for AetherGit commits."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class AetherCommit(BaseModel):
    """Versioned commit in the AetherGit DAG.

    Each commit records performance metrics, tape references, and whether
    it has been approved by the Prime meta-agent for self-evolution.
    """

    id: UUID = Field(default_factory=uuid4)
    parent_ids: list[UUID] = []
    author: str
    timestamp: datetime = Field(default_factory=_utcnow)
    message: str
    commit_type: str
    scope: str
    performance_metrics: dict[str, float] = {}
    confidence_score: float = 0.0
    tape_references: list[UUID] = []
    tree_id: UUID | None = None
    proposed_by: str | None = None
    evolution_approved: bool = False
