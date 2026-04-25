"""Prime meta-agent router (introspection, proposals, skill evolution)."""

from uuid import UUID

from fastapi import APIRouter

from services.api.dependencies import (
    get_introspector,
    get_proposal_engine,
)

router = APIRouter(prefix="/prime", tags=["prime"])


@router.get("/snapshot")
async def snapshot() -> dict[str, object]:
    """Get a full system snapshot from Prime."""
    introspector = get_introspector()
    snap = await introspector.snapshot()
    return snap.model_dump()


@router.get("/proposals")
async def list_proposals(
    user_id: str | None = None,
) -> list[dict[str, object]]:
    """List all proposals, optionally personalized for a user."""
    engine = get_proposal_engine()
    proposals = await engine.list_proposals(user_id=user_id)
    return [p.model_dump() for p in proposals]


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: UUID) -> dict[str, object]:
    """Get a proposal by ID."""
    engine = get_proposal_engine()
    proposal = await engine.get_proposal(proposal_id)
    return proposal.model_dump()


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: UUID, reviewer: str) -> dict[str, object]:
    """Approve a proposal."""
    engine = get_proposal_engine()
    proposal = await engine.approve(proposal_id, reviewer)
    return proposal.model_dump()



@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: UUID, reviewer: str, reason: str = "") -> dict[str, object]:
    """Reject a proposal."""
    engine = get_proposal_engine()
    proposal = await engine.reject(proposal_id, reviewer, reason)
    return proposal.model_dump()



@router.get("/proposals/summarize")
async def summarize_proposals() -> list[dict[str, object]]:
    """Get a summary of all proposals."""
    engine = get_proposal_engine()
    summaries = await engine.summarize()
    return [s.model_dump() for s in summaries]
