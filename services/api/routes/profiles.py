"""User Profile & Intelligence Profile router.

Provides endpoints for both the new UserProfile system (goals, skills,
working style, patterns) and the backward-compatible IntelligenceProfile
system (domain expertise, preference inference, snapshots, rollback).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.profile import (
    InteractionType,
    PreferenceCategory,
    ProfileNotFoundError,
    SnapshotNotFoundError,
)
from services.api.dependencies import (
    IntelligenceProfileServiceDep,
    ProfileStorageDep,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


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


class SetUserProfilePreferenceRequest(BaseModel):
    """Request body for setting a UserProfile preference."""

    key: str
    value: object
    category: str = "general"


class UpdateWorkingStyleRequest(BaseModel):
    """Request body for updating working style."""

    primary_style: str | None = None
    automation_preference: str | None = None
    communication_style: str | None = None
    preferred_session_length: int | None = None
    timezone: str | None = None


class AddGoalRequest(BaseModel):
    """Request body for adding a goal."""

    title: str
    description: str = ""
    category: str = "general"
    priority: int = 3


class UpdateGoalRequest(BaseModel):
    """Request body for updating a goal."""

    status: str | None = None
    progress: float | None = None
    description: str | None = None
    priority: int | None = None


class AddSkillRequest(BaseModel):
    """Request body for adding/updating a learned skill."""

    skill_id: str
    name: str
    category: str = "general"
    proficiency: float = 0.0


class UpdateProfileRequest(BaseModel):
    """Request body for updating core profile fields."""

    display_name: str | None = None
    email: str | None = None
    bio: str | None = None


class RecordPatternRequest(BaseModel):
    """Request body for recording an interaction pattern."""

    pattern_type: str
    pattern_value: str
    confidence: float = 0.5


class RecordSessionRequest(BaseModel):
    """Request body for recording a session."""

    duration: float
    interactions: int = 0
    domains: list[str] | None = None


# ---------------------------------------------------------------------------
# IntelligenceProfile endpoints (backward-compatible)
# ---------------------------------------------------------------------------


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
    return profile.model_dump(mode="json")


@router.get("/{user_id}")
async def get_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get a user's intelligence profile."""
    try:
        profile = await svc.get_profile(user_id)
        return profile.model_dump(mode="json")
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}")
async def get_or_create_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Get or create a user's intelligence profile."""
    profile = await svc.get_or_create_profile(user_id)
    return profile.model_dump(mode="json")


@router.get("")
async def list_profiles(
    svc: IntelligenceProfileServiceDep,
) -> list[dict[str, object]]:
    """List all intelligence profiles."""
    profiles = await svc.list_profiles()
    return [p.model_dump(mode="json") for p in profiles]


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
    return profile.model_dump(mode="json")


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
        return snapshot.model_dump(mode="json")
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
        return [s.model_dump(mode="json") for s in snapshots]
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
        return profile.model_dump(mode="json")
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
    return profile.model_dump(mode="json")


@router.post("/{user_id}/archive")
async def archive_profile(
    user_id: str,
    svc: IntelligenceProfileServiceDep,
) -> dict[str, object]:
    """Archive a user profile."""
    try:
        profile = await svc.archive_profile(user_id)
        return profile.model_dump(mode="json")
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
        return profile.model_dump(mode="json")
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
        return profile.model_dump(mode="json")
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# UserProfile endpoints (new profile features)
# ---------------------------------------------------------------------------


@router.get("/{user_id}/summary")
async def get_profile_summary(
    user_id: str,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Get a summary of the user's full profile."""
    try:
        return await storage.get_profile_summary(user_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{user_id}/details")
async def update_profile_details(
    user_id: str,
    body: UpdateProfileRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Update core profile fields (display_name, email, bio)."""
    updates = body.model_dump(exclude_none=True)
    try:
        profile = await storage.update_profile(user_id, updates)
        return profile.model_dump(mode="json")
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/user-preferences")
async def set_user_preference(
    user_id: str,
    body: SetUserProfilePreferenceRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Set a UserProfile preference (key-value pair)."""
    profile = await storage.set_preference(
        user_id=user_id,
        key=body.key,
        value=body.value,
        category=body.category,
    )
    return profile.model_dump(mode="json")


@router.patch("/{user_id}/working-style")
async def update_working_style(
    user_id: str,
    body: UpdateWorkingStyleRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Update the user's working style configuration."""
    updates = body.model_dump(exclude_none=True)
    profile = await storage.update_working_style(user_id, **updates)
    return profile.model_dump(mode="json")


@router.post("/{user_id}/goals")
async def add_goal(
    user_id: str,
    body: AddGoalRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Add a new goal for the user."""
    goal = await storage.add_goal(
        user_id=user_id,
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
    )
    return goal.model_dump(mode="json")


@router.get("/{user_id}/goals")
async def list_goals(
    user_id: str,
    storage: ProfileStorageDep,
    status: str | None = None,
) -> list[dict[str, object]]:
    """List goals for a user."""
    try:
        goals = await storage.list_goals(user_id, status=status)
        return [g.model_dump(mode="json") for g in goals]
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{user_id}/goals/{goal_id}")
async def update_goal(
    user_id: str,
    goal_id: str,
    body: UpdateGoalRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Update a goal."""
    updates = body.model_dump(exclude_none=True)
    try:
        goal = await storage.update_goal(user_id, goal_id, **updates)
        return goal.model_dump(mode="json")
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/goals/{goal_id}/complete")
async def complete_goal(
    user_id: str,
    goal_id: str,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Mark a goal as completed."""
    try:
        goal = await storage.complete_goal(user_id, goal_id)
        return goal.model_dump(mode="json")
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{user_id}/goals/{goal_id}")
async def delete_goal(
    user_id: str,
    goal_id: str,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Delete a goal."""
    deleted = await storage.delete_goal(user_id, goal_id)
    return {"deleted": deleted}


@router.post("/{user_id}/skills")
async def add_skill(
    user_id: str,
    body: AddSkillRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Add or update a learned skill."""
    skill = await storage.add_or_update_skill(
        user_id=user_id,
        skill_id=body.skill_id,
        name=body.name,
        category=body.category,
        proficiency=body.proficiency,
    )
    return skill.model_dump(mode="json")


@router.get("/{user_id}/skills")
async def list_skills(
    user_id: str,
    storage: ProfileStorageDep,
    category: str | None = None,
) -> list[dict[str, object]]:
    """List skills for a user."""
    try:
        skills = await storage.list_skills(user_id, category=category)
        return [s.model_dump(mode="json") for s in skills]
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/patterns")
async def record_pattern(
    user_id: str,
    body: RecordPatternRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Record an interaction pattern."""
    pattern = await storage.record_pattern(
        user_id=user_id,
        pattern_type=body.pattern_type,
        pattern_value=body.pattern_value,
        confidence=body.confidence,
    )
    return pattern.model_dump(mode="json")


@router.get("/{user_id}/patterns")
async def list_patterns(
    user_id: str,
    storage: ProfileStorageDep,
    pattern_type: str | None = None,
    min_confidence: float = 0.0,
) -> list[dict[str, object]]:
    """List interaction patterns for a user."""
    try:
        patterns = await storage.list_patterns(
            user_id, pattern_type=pattern_type, min_confidence=min_confidence
        )
        return [p.model_dump(mode="json") for p in patterns]
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{user_id}/sessions")
async def record_session(
    user_id: str,
    body: RecordSessionRequest,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Record a completed session."""
    summary = await storage.record_session(
        user_id=user_id,
        duration=body.duration,
        interactions=body.interactions,
        domains=body.domains,
    )
    return summary.model_dump(mode="json")


@router.post("/{user_id}/sync")
async def sync_to_aethergit(
    user_id: str,
    storage: ProfileStorageDep,
    commit_message: str = "Update user profile",
) -> dict[str, object]:
    """Sync profile to AetherGit."""
    commit_id = await storage.sync_to_aethergit(user_id, commit_message)
    return {"commit_id": commit_id}


@router.get("/{user_id}/export")
async def export_profile(
    user_id: str,
    storage: ProfileStorageDep,
) -> dict[str, object]:
    """Export a profile as a JSON dictionary."""
    try:
        return await storage.export_profile(user_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
