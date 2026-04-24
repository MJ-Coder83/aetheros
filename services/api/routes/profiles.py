"""Intelligence Profile router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.intelligence_profile import (
    InteractionType,
    PreferenceCategory,
    ProfileNotFoundError,
    SnapshotNotFoundError,
)
from services.api.dependencies import IntelligenceProfileServiceDep

router = APIRouter(prefix="/profiles", tags=["profiles"])


class RecordInteractionRequest(BaseModel):
    """Request body for recording a user interaction."""

    user_id: str
    interaction_type: str
    domain: str | None = None
    depth: float = 0.5
    approved: bool | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SetPreferenceRequest(BaseModel):
    """Request body for setting a user preference."""

    user_id: str
    category: str
    value: float


@router.post("/interactions")
async def record_interaction(
    body: RecordInteractionRequest,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Record a user interaction and update their profile."""
    itype = InteractionType(body.interaction_type)
    profile = await svc.record_interaction(
        user_id=body.user_id,
        interaction_type=itype,
        domain=body.domain,
        depth=body.depth,
        approved=body.approved,
        metadata=body.metadata,
    )
    return profile.model_dump()


@router.get("/{user_id}")
async def get_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get a user's intelligence profile."""
    try:
        profile = await svc.get_profile(user_id)
        return profile.model_dump()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}")
async def get_or_create_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get or create a user's intelligence profile."""
    profile = await svc.get_or_create_profile(user_id)
    return profile.model_dump()


@router.get("")
async def list_profiles(
    svc: IntelligenceProfileServiceDep,
) -> list[dict[str, object]]:
    """List all intelligence profiles."""
    profiles = await svc.list_profiles()
    return [p.model_dump() for p in profiles]


@router.post("/preferences")
async def set_preference(
    body: SetPreferenceRequest,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Set an explicit user preference."""
    category = PreferenceCategory(body.category)
    profile = await svc.set_preference(
        user_id=body.user_id,
        category=category,
        value=body.value,
    )
    return profile.model_dump()


@router.get("/{user_id}/preferences/{category}")
async def get_effective_preference(
    user_id: str,
    category: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get the effective preference value for a user and category."""
    cat = PreferenceCategory(category)
    value = await svc.get_effective_preference(user_id, cat)
    return {"category": category, "value": value}


@router.post("/{user_id}/snapshots")
async def create_profile_snapshot(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
    reason: str = "",
) -> dict[str, object]:
    """Create a snapshot of a user's profile."""
    try:
        snapshot = await svc.create_snapshot(user_id, reason=reason)
        return snapshot.model_dump()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/snapshots")
async def list_profile_snapshots(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> list[dict[str, object]]:
    """List all snapshots for a user's profile."""
    try:
        snapshots = await svc.list_snapshots(user_id)
        return [s.model_dump() for s in snapshots]
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/rollback/{snapshot_id}")
async def rollback_profile(
    user_id: str,
    snapshot_id: UUID,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Rollback a profile to a specific snapshot."""
    try:
        profile = await svc.rollback_to_snapshot(user_id, snapshot_id)
        return profile.model_dump()
    except (ProfileNotFoundError, SnapshotNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/domains")
async def get_domain_summary(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, dict[str, object]]:
    """Get a summary of all domain expertise for a user."""
    try:
        return await svc.get_domain_summary(user_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{user_id}/context")
async def get_recommendation_context(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get a recommendation context for adapting Prime behaviour."""
    return await svc.get_recommendation_context(user_id)


@router.post("/merge")
async def merge_profiles(
    svc: IntelligenceProfileServiceDep,
    source_user_id: str = "",
    target_user_id: str = "",
) -> dict[str, object]:
    """Merge source profile into target profile."""
    profile = await svc.merge_profiles(source_user_id, target_user_id)
    return profile.model_dump()


@router.post("/{user_id}/archive")
async def archive_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Archive a user profile."""
    try:
        profile = await svc.archive_profile(user_id)
        return profile.model_dump()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/suspend")
async def suspend_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Suspend a user profile."""
    try:
        profile = await svc.suspend_profile(user_id)
        return profile.model_dump()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/reactivate")
async def reactivate_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Reactivate a suspended or archived profile."""
    try:
        profile = await svc.reactivate_profile(user_id)
        return profile.model_dump()
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
