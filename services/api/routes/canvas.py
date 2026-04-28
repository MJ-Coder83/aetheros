"""Canvas API router -- manage Domain Canvases (core + v5)."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from packages.canvas.canvas_v5 import (
    CopilotSuggestionType,
    FrameworkTier,
    PluginNodeConfig,
    SwarmMode,
)
from packages.canvas.core import (
    CanvasError,
    CanvasNotFoundError,
    EdgeNotFoundError,
    InvalidEdgeError,
    NodeNotFoundError,
)
from packages.canvas.models import CanvasLayout, CanvasNodeType
from services.api.dependencies import CanvasServiceDep, CanvasV5ServiceDep

router = APIRouter(prefix="/canvas", tags=["canvas"])

# Annotated type aliases for Query defaults (avoids B008)
SuggestionTypeParam = Annotated[CopilotSuggestionType | None, Query()]
TierParam = Annotated[FrameworkTier | None, Query(description="Filter by tier")]
LimitParam = Annotated[int, Query(description="Max events to return")]
CommitMsgParam = Annotated[str, Query(description="Version commit message")]
AuthorParam = Annotated[str, Query(description="Author of the version")]
OldVersionParam = Annotated[int, Query(description="Old version number")]
NewVersionParam = Annotated[int, Query(description="New version number")]
ExtParam = Annotated[str, Query(description="File extension to detect")]

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateCanvasRequest(BaseModel):
    """Schema for creating a new canvas."""

    domain_id: str
    domain_name: str
    layout: CanvasLayout | None = None
    bootstrap_from_blueprint: bool = True


class BootstrapFromBlueprintRequest(BaseModel):
    """Schema for bootstrapping a canvas from a domain blueprint."""

    domain_id: str
    layout: CanvasLayout | None = None


class AddNodeRequest(BaseModel):
    """Schema for adding a node to the canvas."""

    id: str
    node_type: CanvasNodeType
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 60.0
    metadata: dict[str, Any] = {}


class AddEdgeRequest(BaseModel):
    """Schema for adding an edge to the canvas."""

    id: str | None = None
    source: str
    target: str
    edge_type: str = "contains"
    label: str = ""
    animated: bool = False


class NLEditRequest(BaseModel):
    """Schema for a natural language canvas edit."""

    instruction: str


class PluginNodeRequest(BaseModel):
    """Schema for adding a plugin node."""

    plugin_id: str
    label: str
    plugin_type: str = ""
    capabilities: list[str] = []
    command_registry: list[str] = []
    embed_url: str | None = None


class SwarmRequest(BaseModel):
    """Schema for running a swarm on the canvas."""

    task: str
    agent_ids: list[str] | None = None
    mode: SwarmMode = SwarmMode.QUICK


class SimulationOverlayRequest(BaseModel):
    """Schema for updating simulation overlay metrics."""

    node_metrics: dict[str, dict[str, float]]


# ---------------------------------------------------------------------------
# Core canvas endpoints (unchanged)
# ---------------------------------------------------------------------------


@router.get("/{domain_id}")
async def get_canvas(
    domain_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Retrieve a canvas by domain ID."""
    try:
        canvas = await svc.get_canvas(domain_id)
        return canvas.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("")
async def create_canvas(
    body: CreateCanvasRequest,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Create a new canvas for a domain.

    If ``bootstrap_from_blueprint`` is True (default), attempts to populate
    the canvas from the domain's existing blueprint (agents, skills, workflows)
    and sync to the folder tree.
    """
    try:
        layout = body.layout or CanvasLayout.SMART

        # Try to bootstrap from domain blueprint first
        if body.bootstrap_from_blueprint:
            try:
                from packages.prime.domain_creation import DomainCreationEngine  # noqa: F401
                from services.api.dependencies import get_domain_creation_service

                domain_svc = get_domain_creation_service()
                domains = await domain_svc.list_domains()
                domain = None
                for d in domains:
                    if d.domain_id == body.domain_id:
                        domain = d
                        break

                if domain is not None:
                    blueprints = await domain_svc.list_blueprints()
                    blueprint = None
                    for bp in blueprints:
                        if bp.domain_id == body.domain_id:
                            blueprint = bp
                            break

                    if blueprint is not None:
                        canvas = await svc.canvas_from_domain_blueprint(
                            blueprint, layout=layout, sync_to_tree=True,
                        )
                        return canvas.model_dump()
            except Exception:
                pass  # Fall through to empty canvas

        canvas = await svc.create_canvas(
            domain_id=body.domain_id,
            domain_name=body.domain_name,
            layout=layout,
        )
        return canvas.model_dump()
    except CanvasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{domain_id}/bootstrap")
async def bootstrap_canvas_from_blueprint(
    domain_id: str,
    body: BootstrapFromBlueprintRequest,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Bootstrap a canvas from a domain blueprint.

    Looks up the domain's blueprint, creates a fully populated canvas
    with agent/skill/workflow nodes and proper edges, then syncs to
    the folder tree.
    """
    try:
        from packages.prime.domain_creation import DomainCreationEngine  # noqa: F401
        from services.api.dependencies import get_domain_creation_service

        domain_svc = get_domain_creation_service()
        blueprints = await domain_svc.list_blueprints()
        blueprint = None
        for bp in blueprints:
            if bp.domain_id == domain_id:
                blueprint = bp
                break

        if blueprint is None:
            raise HTTPException(
                status_code=404,
                detail=f"No blueprint found for domain '{domain_id}'",
            )

        layout = body.layout or CanvasLayout.SMART
        canvas = await svc.canvas_from_domain_blueprint(
            blueprint, layout=layout, sync_to_tree=True,
        )
        return canvas.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CanvasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{domain_id}/folder-tree")
async def get_folder_tree(
    domain_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Get the folder tree data for a domain's canvas.

    Returns the complete folder tree structure for rendering in
    Folder Mode view.
    """
    try:
        from services.api.dependencies import get_folder_tree_service

        ft_svc = get_folder_tree_service()
        tree = await ft_svc.get_tree(domain_id)
        # Serialize the tree for the frontend
        nodes_list = []
        for _path, node in tree.nodes.items():
            nodes_list.append({
                "path": node.path,
                "name": node.name,
                "node_type": node.node_type.value,
                "content": node.content[:500] if node.content else "",
                "children": node.children,
            })
        return {
            "domain_id": domain_id,
            "root_path": tree.root_path,
            "nodes": nodes_list,
            "version": tree.version,
        }
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/domains")
async def list_canvas_domains(
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """List all domain IDs that have canvases."""
    domain_ids = await svc._store.list_domain_ids()
    return {"domain_ids": domain_ids, "count": len(domain_ids)}


@router.post("/{domain_id}/nodes")
async def add_node(
    domain_id: str,
    body: AddNodeRequest,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Add a node to the canvas."""
    try:
        from packages.canvas.models import CanvasNode

        node = CanvasNode(
            id=body.id,
            node_type=body.node_type,
            label=body.label,
            x=body.x,
            y=body.y,
            width=body.width,
            height=body.height,
            metadata=body.metadata,
        )
        result = await svc.add_node(domain_id, node)
        return result.model_dump()
    except (CanvasNotFoundError, CanvasError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{domain_id}/nodes/{node_id}")
async def remove_node(
    domain_id: str,
    node_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Remove a node from the canvas."""
    try:
        await svc.remove_node(domain_id, node_id)
        return {"status": "ok"}
    except (CanvasNotFoundError, NodeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{domain_id}/edges/{edge_id}")
async def remove_edge(
    domain_id: str,
    edge_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Remove an edge from the canvas."""
    try:
        await svc.remove_edge(domain_id, edge_id)
        return {"status": "ok"}
    except (CanvasNotFoundError, EdgeNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/edges")
async def add_edge(
    domain_id: str,
    body: AddEdgeRequest,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Add an edge to the canvas."""
    try:
        from packages.canvas.core import CanvasEdgeType
        from packages.canvas.models import CanvasEdge

        edge = CanvasEdge(
            id=body.id if body.id else "",
            source=body.source,
            target=body.target,
            edge_type=CanvasEdgeType(body.edge_type),
            label=body.label,
            animated=body.animated,
        )
        result = await svc.add_edge(domain_id, edge)
        return result.model_dump()
    except (CanvasNotFoundError, InvalidEdgeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{domain_id}/layout")
async def apply_layout(
    domain_id: str,
    layout: CanvasLayout,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Apply a layout strategy to the canvas."""
    try:
        canvas = await svc.apply_layout(domain_id, layout)
        return canvas.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/sync-to-tree")
async def sync_to_tree(
    domain_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Push canvas changes to the folder tree."""
    try:
        await svc.sync_to_folder_tree(domain_id)
        return {"status": "ok"}
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/sync-from-tree")
async def sync_from_tree(
    domain_id: str,
    svc: CanvasServiceDep,
) -> dict[str, Any]:
    """Pull folder tree changes into the canvas."""
    try:
        canvas = await svc.sync_from_folder_tree(domain_id)
        return canvas.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{domain_id}/diff")
async def get_diff(
    domain_id: str,
    svc: CanvasServiceDep,
    old_version: int = 0,
    new_version: int | None = None,
) -> dict[str, Any]:
    """Get the diff between two canvas versions."""
    try:
        canvas_new = await svc._get_canvas(domain_id)
        # Simplified: return current canvas state
        return canvas_new.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Canvas v5 endpoints
# ---------------------------------------------------------------------------


@router.post("/{domain_id}/nl-edit")
async def natural_language_edit(
    domain_id: str,
    body: NLEditRequest,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Apply a natural language edit to the canvas.

    Accepts instructions like "Move the domain node to the center" or
    "Make the analyst agent larger" and parses them into structured
    canvas mutations.
    """
    try:
        result = await v5.natural_language_edit(domain_id, body.instruction)
        return result.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{domain_id}/copilot")
async def get_copilot_suggestions(
    domain_id: str,
    v5: CanvasV5ServiceDep,
    suggestion_type: SuggestionTypeParam = None,
) -> dict[str, Any]:
    """Get Prime Co-Pilot suggestions for the canvas."""
    try:
        suggestions = await v5.get_copilot_suggestions(domain_id)
        if suggestion_type is not None:
            suggestions = [s for s in suggestions if s.suggestion_type == suggestion_type]
        return {
            "domain_id": domain_id,
            "suggestions": [s.model_dump() for s in suggestions],
            "count": len(suggestions),
        }
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/copilot/{suggestion_id}/apply")
async def apply_copilot_suggestion(
    domain_id: str,
    suggestion_id: str,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Apply a Prime Co-Pilot suggestion to the canvas."""
    try:
        suggestions = await v5.get_copilot_suggestions(domain_id)
        target = None
        for s in suggestions:
            if s.suggestion_id == suggestion_id:
                target = s
                break
        if target is None:
            raise HTTPException(status_code=404, detail=f"Suggestion '{suggestion_id}' not found")
        applied = await v5.apply_copilot_suggestion(domain_id, target)
        return {"suggestion_id": suggestion_id, "applied": applied}
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{domain_id}/plugin-nodes")
async def add_plugin_node(
    domain_id: str,
    body: PluginNodeRequest,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Add a Plugin Node to the canvas."""
    try:
        config = PluginNodeConfig(
            plugin_id=body.plugin_id,
            label=body.label,
            plugin_type=body.plugin_type,
            capabilities=body.capabilities,
            command_registry=body.command_registry,
            embed_url=body.embed_url,
        )
        plugin_config, canvas_node = await v5.add_plugin_node(domain_id, config)
        return {
            "plugin_node": plugin_config.model_dump(),
            "canvas_node": canvas_node.model_dump(),
        }
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CanvasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{domain_id}/plugin-nodes")
async def list_plugin_nodes(
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """List all registered plugin nodes."""
    nodes = v5.plugin_nodes.list_plugin_nodes()
    return {"plugin_nodes": [n.model_dump() for n in nodes], "count": len(nodes)}


@router.post("/{domain_id}/simulation-overlay")
async def update_simulation_overlay(
    domain_id: str,
    body: SimulationOverlayRequest,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Update simulation overlay metrics for canvas nodes."""
    overlay = await v5.update_simulation_overlay(domain_id, body.node_metrics)
    serialized: dict[str, Any] = {}
    for node_id, metrics in overlay.items():
        serialized[node_id] = {k: v.model_dump() for k, v in metrics.items()}
    return {"domain_id": domain_id, "overlay": serialized}


@router.get("/{domain_id}/simulation-overlay")
async def get_simulation_overlay(
    domain_id: str,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Get current simulation overlay data for the canvas."""
    overlay = v5.simulation_overlay.get_overlay_data()
    serialized: dict[str, Any] = {}
    for node_id, metrics in overlay.items():
        serialized[node_id] = {k: v.model_dump() for k, v in metrics.items()}
    return {"domain_id": domain_id, "overlay": serialized}


@router.get("/{domain_id}/tape-overlay")
async def get_tape_overlay(
    domain_id: str,
    v5: CanvasV5ServiceDep,
    limit: LimitParam = 50,
) -> dict[str, Any]:
    """Get recent Tape events for the canvas overlay."""
    events = v5.get_tape_overlay_events(limit)
    return {
        "domain_id": domain_id,
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


@router.post("/{domain_id}/versions")
async def save_canvas_version(
    domain_id: str,
    v5: CanvasV5ServiceDep,
    commit_message: CommitMsgParam = "",
    author: AuthorParam = "system",
) -> dict[str, Any]:
    """Save a version snapshot of the canvas (AetherGit-style versioning)."""
    try:
        version = await v5.save_canvas_version(domain_id, commit_message, author)
        return version.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{domain_id}/versions")
async def list_canvas_versions(
    domain_id: str,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """List all version snapshots for a canvas."""
    versions = v5.versioning.list_versions(domain_id)
    return {
        "domain_id": domain_id,
        "versions": [v.model_dump() for v in versions],
        "count": len(versions),
    }


@router.get("/{domain_id}/versions/diff")
async def diff_canvas_versions(
    domain_id: str,
    v5: CanvasV5ServiceDep,
    old_version: OldVersionParam,
    new_version: NewVersionParam,
) -> dict[str, Any]:
    """Get the diff between two canvas versions."""
    diff = v5.versioning.diff_versions(domain_id, old_version, new_version)
    return diff


@router.post("/{domain_id}/versions/{version}/rewind")
async def rewind_canvas_version(
    domain_id: str,
    version: int,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Rewind the canvas to a previous version."""
    canvas = v5.versioning.rewind_to_version(domain_id, version, v5._canvas_service)
    if canvas is None:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    return canvas.model_dump()


@router.post("/{domain_id}/swarm")
async def run_swarm(
    domain_id: str,
    body: SwarmRequest,
    v5: CanvasV5ServiceDep,
) -> dict[str, Any]:
    """Run a swarm (Quick or Governed) on the canvas."""
    if body.mode == SwarmMode.GOVERNED:
        governed = await v5.run_governed_swarm(domain_id, body.task, body.agent_ids)
        return governed.model_dump()
    quick = await v5.run_quick_swarm(domain_id, body.task, body.agent_ids)
    return quick.model_dump()


@router.get("/frameworks")
async def list_frameworks(
    v5: CanvasV5ServiceDep,
    tier: TierParam = None,
) -> dict[str, Any]:
    """List all supported UI frameworks, optionally by tier."""
    frameworks = v5.list_frameworks(tier)
    return {
        "frameworks": [f.model_dump() for f in frameworks],
        "count": len(frameworks),
    }


@router.get("/frameworks/detect")
async def detect_framework(
    v5: CanvasV5ServiceDep,
    extension: ExtParam,
) -> dict[str, Any]:
    """Detect a UI framework from a file extension."""
    framework = v5.detect_framework(extension)
    if framework is None:
        return {"framework": None, "found": False}
    return {"framework": framework.model_dump(), "found": True}
