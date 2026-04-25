"""Canvas API router — manage Domain Canvases."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.canvas.core import (
    CanvasError,
    CanvasNotFoundError,
    EdgeNotFoundError,
    InvalidEdgeError,
    NodeNotFoundError,
)
from packages.canvas.models import CanvasLayout, CanvasNodeType
from services.api.dependencies import CanvasServiceDep

router = APIRouter(prefix="/canvas", tags=["canvas"])


class CreateCanvasRequest(BaseModel):
    """Schema for creating a new canvas."""
    domain_id: str
    domain_name: str
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
    """Create a new canvas for a domain."""
    try:
        layout = body.layout or CanvasLayout.SMART
        canvas = await svc.create_canvas(
            domain_id=body.domain_id,
            domain_name=body.domain_name,
            layout=layout,
        )
        return canvas.model_dump()
    except CanvasError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        canvas_new = svc._get_canvas(domain_id)
        # Simplified: return current canvas state
        return canvas_new.model_dump()
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
