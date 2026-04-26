"""Marketplace API routes — plugin discovery, installation, rating, and permissions."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.marketplace.service import (
    AlreadyRatedError,
    DuplicateInstallationError,
    DuplicateListingError,
    InstallationNotFoundError,
    InsufficientPermissionLevelError,
    PermissionRequest,
    PermissionRequestNotFoundError,
    PluginCategory,
    PluginInstallation,
    PluginListing,
    PluginNotFoundError,
    PluginPermissionLevel,
    PluginRating,
    PluginSortOrder,
    RatingValidationError,
    SelfRatingError,
)
from services.api.dependencies import MarketplaceServiceDep

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class PublishPluginRequest(BaseModel):
    name: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    category: PluginCategory
    tags: list[str] = Field(default_factory=list)
    permissions: list[PluginPermissionLevel] = Field(default_factory=list)
    homepage_url: str = ""
    repository_url: str = ""
    icon_url: str = ""
    is_featured: bool = False
    min_platform_version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Module-level Query singletons (avoids B008)
# ---------------------------------------------------------------------------

_q_required = Query(...)
_q_empty = Query("")
_q_false = Query(False)
_q_sort_newest = Query(PluginSortOrder.NEWEST)
_q_limit = Query(20, ge=1, le=100)
_q_offset = Query(0, ge=0)
_q_score = Query(..., ge=1, le=5)


# ---------------------------------------------------------------------------
# Plugin publishing
# ---------------------------------------------------------------------------


@router.post("/plugins", response_model=PluginListing, status_code=201)
async def publish_plugin(
    svc: MarketplaceServiceDep,
    body: PublishPluginRequest,
) -> PluginListing:
    """Publish a new plugin to the marketplace."""
    try:
        return await svc.publish_plugin(
            name=body.name,
            display_name=body.display_name,
            description=body.description,
            version=body.version,
            author=body.author,
            category=body.category,
            tags=body.tags,
            permissions=body.permissions,
            homepage_url=body.homepage_url,
            repository_url=body.repository_url,
            icon_url=body.icon_url,
            is_featured=body.is_featured,
            min_platform_version=body.min_platform_version,
        )
    except (DuplicateListingError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Discovery & search
# ---------------------------------------------------------------------------


@router.get("/discover", response_model=list[PluginListing])
async def discover_plugins(
    svc: MarketplaceServiceDep,
    category: PluginCategory | None = None,
    tags: str = _q_empty,
    featured_only: bool = _q_false,
    sort: PluginSortOrder = _q_sort_newest,
    limit: int = _q_limit,
    offset: int = _q_offset,
) -> list[PluginListing]:
    """Browse plugins with optional category/tag filters."""
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return await svc.discover(
        category=category,
        tags=parsed_tags,
        featured_only=featured_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[PluginListing])
async def search_plugins(
    svc: MarketplaceServiceDep,
    q: str = _q_required,
    category: PluginCategory | None = None,
    sort: PluginSortOrder = _q_sort_newest,
    limit: int = _q_limit,
    offset: int = _q_offset,
) -> list[PluginListing]:
    """Full-text search across plugin metadata."""
    return await svc.search(
        query=q,
        category=category,
        sort=sort,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Plugin details
# ---------------------------------------------------------------------------


@router.get("/plugins/{plugin_id}", response_model=PluginListing)
async def get_plugin(
    plugin_id: UUID,
    svc: MarketplaceServiceDep,
) -> PluginListing:
    """Get detailed plugin information by ID."""
    try:
        return await svc.get_plugin(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------


@router.post("/plugins/{plugin_id}/install", status_code=201)
async def install_plugin(
    plugin_id: UUID,
    svc: MarketplaceServiceDep,
    domain_id: str = _q_required,
    user_id: str = _q_required,
) -> dict[str, object]:
    """Install a plugin into a domain."""
    try:
        installation, perm_request = await svc.install(
            plugin_id=plugin_id,
            domain_id=domain_id,
            user_id=user_id,
        )
    except (PluginNotFoundError, DuplicateInstallationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result: dict[str, object] = {
        "installation": installation.model_dump(),
    }
    if perm_request is not None:
        result["permission_request"] = perm_request.model_dump()
    return result


@router.delete("/installations/{installation_id}")
async def uninstall_plugin(
    installation_id: UUID,
    svc: MarketplaceServiceDep,
    domain_id: str = _q_required,
) -> dict[str, object]:
    """Uninstall a plugin from a domain."""
    try:
        installation = await svc.uninstall(installation_id, domain_id)
        return installation.model_dump()
    except InstallationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/installations/{installation_id}", response_model=PluginInstallation)
async def get_installation(
    installation_id: UUID,
    svc: MarketplaceServiceDep,
) -> PluginInstallation:
    """Get an installation record by ID."""
    try:
        return await svc.get_installation(installation_id)
    except InstallationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/domains/{domain_id}/installations", response_model=list[PluginInstallation])
async def list_installed(
    domain_id: str,
    svc: MarketplaceServiceDep,
) -> list[PluginInstallation]:
    """List all installed plugins for a domain."""
    return await svc.list_installed(domain_id)


# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------


@router.post("/plugins/{plugin_id}/rate", response_model=PluginRating, status_code=201)
async def rate_plugin(
    plugin_id: UUID,
    svc: MarketplaceServiceDep,
    user_id: str = _q_required,
    score: int = _q_score,
    review: str = _q_empty,
) -> PluginRating:
    """Rate a plugin (1-5 stars)."""
    try:
        return await svc.rate(
            plugin_id=plugin_id,
            user_id=user_id,
            score=score,
            review=review,
        )
    except (
        PluginNotFoundError,
        RatingValidationError,
        AlreadyRatedError,
        SelfRatingError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Permission flow
# ---------------------------------------------------------------------------


@router.post("/permissions/{request_id}/approve")
async def approve_permissions(
    request_id: UUID,
    svc: MarketplaceServiceDep,
    approver_id: str = _q_required,
    approved_permissions: str = _q_empty,
) -> dict[str, object]:
    """Approve a pending permission request."""
    parsed_permissions: list[PluginPermissionLevel] | None = None
    if approved_permissions:
        parsed_permissions = [
            PluginPermissionLevel(p.strip())
            for p in approved_permissions.split(",")
            if p.strip()
        ]

    try:
        perm_request, installation = await svc.approve_permissions(
            request_id=request_id,
            approver_id=approver_id,
            approved_permissions=parsed_permissions,
        )
    except (PermissionRequestNotFoundError, InsufficientPermissionLevelError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "permission_request": perm_request.model_dump(),
        "installation": installation.model_dump() if installation else None,
    }


@router.post("/permissions/{request_id}/reject")
async def reject_permissions(
    request_id: UUID,
    svc: MarketplaceServiceDep,
    rejector_id: str = _q_required,
    reason: str = _q_empty,
) -> dict[str, object]:
    """Reject a pending permission request."""
    try:
        perm_request, installation = await svc.reject_permissions(
            request_id=request_id,
            rejector_id=rejector_id,
            reason=reason,
        )
    except PermissionRequestNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "permission_request": perm_request.model_dump(),
        "installation": installation.model_dump() if installation else None,
    }


@router.get("/domains/{domain_id}/pending-permissions", response_model=list[PermissionRequest])
async def get_pending_permissions(
    domain_id: str,
    svc: MarketplaceServiceDep,
) -> list[PermissionRequest]:
    """List all pending permission requests for a domain."""
    return await svc.get_pending_permissions(domain_id)


# ---------------------------------------------------------------------------
# Plugin management
# ---------------------------------------------------------------------------


@router.patch("/plugins/{plugin_id}", response_model=PluginListing)
async def update_plugin(
    plugin_id: UUID,
    svc: MarketplaceServiceDep,
    description: str | None = None,
    version: str | None = None,
    tags: str = _q_empty,
    homepage_url: str | None = None,
    repository_url: str | None = None,
    icon_url: str | None = None,
    is_featured: bool | None = None,
) -> PluginListing:
    """Update an existing plugin listing."""
    parsed_tags: list[str] | None = None
    if tags:
        parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        return await svc.update_plugin(
            plugin_id=plugin_id,
            description=description,
            version=version,
            tags=parsed_tags,
            homepage_url=homepage_url,
            repository_url=repository_url,
            icon_url=icon_url,
            is_featured=is_featured,
        )
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/plugins/{plugin_id}")
async def unpublish_plugin(
    plugin_id: UUID,
    svc: MarketplaceServiceDep,
) -> dict[str, object]:
    """Remove a plugin from the marketplace."""
    try:
        listing = await svc.unpublish_plugin(plugin_id)
        return listing.model_dump()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
