"""Folder Tree router — Folder Thinking Mode and dual-view Canvas support."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.folder_tree import (
    DomainTreeNotFoundError,
    FolderOperation,
    FolderTreeError,
    PathAlreadyExistsError,
    PathNotFoundError,
)
from services.api.dependencies import FolderTreeServiceDep

router = APIRouter(prefix="/folder-tree", tags=["folder-tree"])


class ReadFileRequest(BaseModel):
    domain_id: str
    path: str


class WriteFileRequest(BaseModel):
    domain_id: str
    path: str
    content: str


class CreateDirectoryRequest(BaseModel):
    domain_id: str
    path: str


class MovePathRequest(BaseModel):
    domain_id: str
    old_path: str
    new_path: str


class DeletePathRequest(BaseModel):
    domain_id: str
    path: str


class SearchRequest(BaseModel):
    domain_id: str
    query: str
    search_content: bool = True
    max_results: int = 20


class SyncFromCanvasRequest(BaseModel):
    domain_id: str
    operations: list[FolderOperation]


@router.get("/{domain_id}")
async def get_tree(
    domain_id: str,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Get the full folder tree for a domain."""
    try:
        tree = await svc.get_tree(domain_id)
        return tree.model_dump()
    except DomainTreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{domain_id}/list")
async def list_directory(
    domain_id: str,
    svc: FolderTreeServiceDep,
    path: str = "",
) -> list[dict[str, object]]:
    """List contents of a directory in the domain's folder tree."""
    try:
        children = await svc.list_directory(domain_id, path)
        return [c.model_dump() for c in children]
    except (DomainTreeNotFoundError, PathNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FolderTreeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/read")
async def read_file(
    body: ReadFileRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Read a file from the domain's folder tree."""
    try:
        node = await svc.read_file(body.domain_id, body.path)
        return node.model_dump()
    except (DomainTreeNotFoundError, PathNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FolderTreeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/write", status_code=201)
async def write_file(
    body: WriteFileRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Write content to a file in the domain's folder tree."""
    try:
        node = await svc.write_file(body.domain_id, body.path, body.content)
        return node.model_dump()
    except DomainTreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/mkdir", status_code=201)
async def create_directory(
    body: CreateDirectoryRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Create a new directory in the domain's folder tree."""
    try:
        node = await svc.create_directory(body.domain_id, body.path)
        return dict(node.model_dump())
    except PathAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DomainTreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/move")
async def move_path(
    body: MovePathRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Move/rename a file or directory."""
    try:
        node = await svc.move_path(body.domain_id, body.old_path, body.new_path)
        return node.model_dump()
    except (DomainTreeNotFoundError, PathNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PathAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/delete")
async def delete_path(
    body: DeletePathRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Delete a file or directory."""
    try:
        await svc.delete_path(body.domain_id, body.path)
        return {"status": "deleted", "domain_id": body.domain_id, "path": body.path}
    except (DomainTreeNotFoundError, PathNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/search")
async def search(
    body: SearchRequest,
    svc: FolderTreeServiceDep,
) -> list[dict[str, object]]:
    """Search files by content."""
    try:
        results = await svc.search(
            body.domain_id, body.query,
            search_content=body.search_content,
            max_results=body.max_results,
        )
        return [r.model_dump() for r in results]
    except DomainTreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync")
async def sync_from_canvas(
    body: SyncFromCanvasRequest,
    svc: FolderTreeServiceDep,
) -> dict[str, object]:
    """Synchronize visual canvas changes into the folder tree."""
    try:
        tree = await svc.sync_from_canvas(body.domain_id, body.operations)
        return tree.model_dump()
    except DomainTreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
