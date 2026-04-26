"""Plugin SDK router — Plugin lifecycle, command execution, and event management.

Provides endpoints for:
- Plugin registration, loading, activation, deactivation, uninstall
- Command handler registration and execution
- Event subscription and publishing
- Plugin discovery (list, search, get)
- Dependency and version compatibility checks
- System-wide plugin statistics
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.plugin.core import (
    DependencyNotSatisfiedError,
    PluginAlreadyRegisteredError,
    PluginCommandNotFoundError,
    PluginNotActiveError,
    PluginNotFoundError,
    PluginTransitionError,
    VersionNotCompatibleError,
)
from packages.plugin.models import (
    PluginCommand,
    PluginDependency,
    PluginEventSubscription,
    PluginManifest,
    PluginPermission,
    PluginType,
    PluginVersion,
)
from services.api.dependencies import PluginSDKDep

router = APIRouter(prefix="/plugins", tags=["plugins"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ManifestRequest(BaseModel):
    """Request body for registering a plugin."""

    id: str
    name: str
    version: str = "0.1.0"
    plugin_type: str = "utility"
    description: str = ""
    author: str = ""
    permissions: list[str] = ["read"]
    commands: list[dict[str, object]] = []
    event_subscriptions: list[dict[str, object]] = []
    events_published: list[str] = []
    dependencies: list[dict[str, object]] = []
    tags: list[str] = []
    min_platform_version: str | None = None
    max_platform_version: str | None = None


class RegisterPluginRequest(BaseModel):
    """Request body for registering a plugin with install metadata."""

    manifest: ManifestRequest
    installed_by: str = ""
    source_url: str = ""
    config: dict[str, object] = Field(default_factory=dict)


class ExecuteCommandRequest(BaseModel):
    """Request body for executing a plugin command."""

    command_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    timeout_ms: int | None = None


class RegisterHandlerRequest(BaseModel):
    """Marker that a command handler should be registered (server-side only)."""

    command_name: str


class SubscribeEventsRequest(BaseModel):
    """Request body for subscribing a plugin to events."""

    event_type: str


class PublishEventRequest(BaseModel):
    """Request body for publishing an event from a plugin."""

    event_type: str
    payload: dict[str, object] = Field(default_factory=dict)


class SearchPluginsRequest(BaseModel):
    """Request body for searching plugins."""

    query: str = ""
    tags: list[str] = []


# ---------------------------------------------------------------------------
# Helper: convert ManifestRequest → PluginManifest
# ---------------------------------------------------------------------------


def _to_manifest(req: ManifestRequest) -> PluginManifest:
    """Convert a ManifestRequest payload to a PluginManifest model."""
    version = PluginVersion.parse(req.version)
    permissions = {PluginPermission(p) for p in req.permissions}
    commands = [
        PluginCommand(
            name=str(c.get("name", "")),
            description=str(c.get("description", "")),
            timeout_ms=int(str(c.get("timeout_ms", 30_000))),
        )
        for c in req.commands
        if c.get("name")
    ]
    event_subs = [
        PluginEventSubscription(
            event_type=str(e.get("event_type", "")),
            description=str(e.get("description", "")),
        )
        for e in req.event_subscriptions
        if e.get("event_type")
    ]
    deps = [
        PluginDependency(
            plugin_id=str(d.get("plugin_id", "")),
            min_version=PluginVersion.parse(str(d.get("min_version", "0.1.0"))),
            optional=bool(d.get("optional", False)),
        )
        for d in req.dependencies
        if d.get("plugin_id")
    ]
    min_pv = PluginVersion.parse(req.min_platform_version) if req.min_platform_version else None
    max_pv = PluginVersion.parse(req.max_platform_version) if req.max_platform_version else None

    return PluginManifest(
        id=req.id,
        name=req.name,
        version=version,
        plugin_type=PluginType(req.plugin_type),
        description=req.description,
        author=req.author,
        permissions=permissions,
        commands=commands,
        event_subscriptions=event_subs,
        events_published=req.events_published,
        dependencies=deps,
        tags=req.tags,
        min_platform_version=min_pv,
        max_platform_version=max_pv,
    )


# ---------------------------------------------------------------------------
# Lifecycle endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def register_plugin(
    body: RegisterPluginRequest,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Register a new plugin from its manifest."""
    try:
        manifest = _to_manifest(body.manifest)
        plugin = await sdk.register_plugin(
            manifest=manifest,
            installed_by=body.installed_by,
            source_url=body.source_url,
            config=dict(body.config),
        )
        return plugin.to_summary()
    except PluginAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{plugin_id}/load")
async def load_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Load a registered plugin, resolving dependencies."""
    try:
        plugin = await sdk.load_plugin(plugin_id)
        return plugin.to_summary()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PluginTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (DependencyNotSatisfiedError, VersionNotCompatibleError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{plugin_id}/activate")
async def activate_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Activate a loaded plugin."""
    try:
        plugin = await sdk.activate_plugin(plugin_id)
        return plugin.to_summary()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PluginTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{plugin_id}/deactivate")
async def deactivate_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Deactivate an active plugin."""
    try:
        plugin = await sdk.deactivate_plugin(plugin_id)
        return plugin.to_summary()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PluginTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{plugin_id}/unload")
async def unload_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Unload a plugin, releasing its runtime resources."""
    try:
        plugin = await sdk.unload_plugin(plugin_id)
        return plugin.to_summary()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PluginTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Fully uninstall a plugin, removing it from the registry."""
    try:
        result = await sdk.uninstall_plugin(plugin_id)
        return {"plugin_id": plugin_id, "removed": result}
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PluginTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Command execution endpoints
# ---------------------------------------------------------------------------


@router.post("/{plugin_id}/commands")
async def execute_command(
    plugin_id: str,
    body: ExecuteCommandRequest,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Execute a command on an active plugin."""
    try:
        execution = await sdk.execute_command(
            plugin_id=plugin_id,
            command_name=body.command_name,
            arguments=dict(body.arguments),
            timeout_ms=body.timeout_ms,
        )
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "result": execution.result,
            "error_message": execution.error_message,
            "execution_time_ms": execution.execution_time_ms,
        }
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PluginNotActiveError, PluginCommandNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Event endpoints
# ---------------------------------------------------------------------------


@router.post("/{plugin_id}/events/subscribe")
async def subscribe_to_events(
    plugin_id: str,
    body: SubscribeEventsRequest,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Subscribe a plugin to an event type."""
    try:
        # Note: The handler is a no-op placeholder for API-level subscription.
        # Real handlers are registered programmatically via the SDK.
        await sdk.subscribe_to_events(
            plugin_id=plugin_id,
            event_type=body.event_type,
            handler=lambda event: None,
        )
        return {"plugin_id": plugin_id, "event_type": body.event_type, "subscribed": True}
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PluginNotActiveError, Exception) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{plugin_id}/events/publish")
async def publish_event(
    plugin_id: str,
    body: PublishEventRequest,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Publish an event from a plugin."""
    try:
        count = await sdk.publish_event(
            plugin_id=plugin_id,
            event_type=body.event_type,
            payload=dict(body.payload),
        )
        return {"plugin_id": plugin_id, "event_type": body.event_type, "subscribers_notified": count}
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (PluginNotActiveError, Exception) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_plugins(
    sdk: PluginSDKDep,
    status: str | None = None,
    plugin_type: str | None = None,
) -> list[dict[str, object]]:
    """List all plugins, optionally filtered by status or type."""
    from packages.plugin.models import PluginStatus as PluginStatusEnum

    status_enum = PluginStatusEnum(status) if status else None
    type_enum = PluginType(plugin_type) if plugin_type else None
    plugins = sdk.list_plugins(status=status_enum, plugin_type=type_enum)
    return [p.to_summary() for p in plugins]


@router.get("/search")
async def search_plugins(
    sdk: PluginSDKDep,
    q: str = "",
    tags: str = "",
) -> list[dict[str, object]]:
    """Search plugins by query string and/or tags."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    plugins = sdk.search_plugins(query=q, tags=tag_list)
    return [p.to_summary() for p in plugins]


@router.get("/stats")
async def get_plugin_stats(
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Get aggregate plugin system statistics."""
    return sdk.get_stats().model_dump()


@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Get a plugin by its manifest ID."""
    try:
        return sdk.get_plugin(plugin_id).to_summary()
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{plugin_id}/dependencies")
async def check_dependencies(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Check if a plugin's dependencies are satisfied."""
    try:
        errors = await sdk.check_dependencies(plugin_id)
        return {"plugin_id": plugin_id, "satisfied": len(errors) == 0, "errors": errors}
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{plugin_id}/version-compat")
async def check_version_compat(
    plugin_id: str,
    sdk: PluginSDKDep,
) -> dict[str, object]:
    """Check if a plugin is compatible with the current platform version."""
    try:
        errors = sdk.check_version_compatibility(plugin_id)
        return {"plugin_id": plugin_id, "compatible": len(errors) == 0, "errors": errors}
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{plugin_id}/execution-log")
async def get_execution_log(
    plugin_id: str,
    sdk: PluginSDKDep,
    limit: int = 100,
) -> list[dict[str, object]]:
    """Get command execution history for a plugin."""
    entries = sdk.get_execution_log(plugin_id=plugin_id, limit=limit)
    return [
        {
            "execution_id": str(e.id),
            "command_name": e.command_name,
            "status": e.status,
            "result": e.result,
            "error_message": e.error_message,
            "execution_time_ms": e.execution_time_ms,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in entries
    ]
